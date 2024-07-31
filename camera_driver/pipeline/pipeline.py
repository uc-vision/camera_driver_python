from dataclasses import replace
from datetime import datetime
import logging
from typing import Set
from beartype.typing import Dict

from camera_driver.data.util import wait_for
import torch
from beartype import beartype
from pydispatch import Dispatcher

from camera_driver.camera_group.camera_set import CameraSet
from camera_driver.camera_group.sync_handler import SyncHandler, TimeQuery
from camera_driver.camera_group.initializer import Initialiser
from camera_driver.driver.interface import Buffer

from .config import CameraPipelineConfig, ImageSettings
from .image.camera_image import CameraImage
from .image.frame_processor import FrameProcessor
from .image.image_outputs import ImageOutputs

from camera_driver.concurrent.taichi_queue import TaichiQueue


class InitException(Exception):
  pass

@beartype
def cameras_from_config(config:CameraPipelineConfig, logger:logging.Logger):

  manager = config.backend.create(config.camera_settings, logger)
  logger.info(f"Found cameras {manager.camera_serials()}")

  missing = {name:serial for name, serial in config.camera_serials.items() if serial not in manager.camera_serials()}
  if len(missing) > 0:
    raise ValueError(f"Camera(s) not found: {missing}")

  if config.reset_cycle is True:
    manager.reset_cameras(set(config.camera_serials.values()))
    cameras = manager.wait_for_cameras(config.camera_serials)

  else:
    cameras = {name:manager.init_camera(name, serial)
            for name, serial in config.camera_serials.items()}

    
  return cameras, manager


class CameraPipeline(Dispatcher):
  _events_ = ["on_image_set", "on_stopped", "on_settings"]

  @beartype
  def __init__(self, config:CameraPipelineConfig, 
               logger:logging.Logger, 
               query_time:TimeQuery):
    
    self.config = config
    self.query_time = query_time

    cameras, manager = cameras_from_config(config, logger)

    
    for k, camera in cameras.items():
      camera.setup_mode("master" if k == config.master else "slave")
      camera.update_properties(config.parameters.camera_properties)

    self.camera_set = CameraSet(cameras, logger, master=config.master)

    self.sync_handler = None
    self.manager = manager
    self.logger = logger

    self.camera_info = {name:camera.camera_info() for name, camera in cameras.items()}

    for info in self.camera_info.values():
      logger.info(str(info))

    self.processor = FrameProcessor(self.camera_info, settings=config.parameters, 
                                    logger=logger, device=torch.device(config.device), 
                                    num_workers=config.process_workers, max_size=config.process_workers)
  

    self.processor.bind(on_frame=self._on_image_set)

  def _on_image_set(self, group:Dict[str, ImageOutputs]):
    self.emit("on_image_set", group)
  
  def _process_buffer(self, buffer:Buffer):
    now = self.query_time()
    return CameraImage.from_buffer(buffer, now, self.processor.device)


  def update_settings(self, image_settings:ImageSettings):
    self.processor.update_settings(image_settings)

    if self.is_started:
      self.camera_set.update_properties(image_settings.camera_properties)

    self.config = replace(self.config, parameters=image_settings)
    self.emit("on_settings", image_settings)

  def initialize_offsets(self):
      init = Initialiser(self.camera_set.camera_ids, 
                         self.query_time, 
                init_window=self.config.init_window, 
                sync_threshold=self.config.sync_threshold_msec / 1000., 
                logger=self.logger)
      
      self.camera_set.bind(on_buffer=init.push_image)
      self.camera_set.start()

      offsets = wait_for(init, 'initialized', self.config.init_timeout_msec / 1000.)
      self.camera_set.stop()

      self.camera_set.unbind(init.push_image)

      if offsets is None:
        raise InitException(f"Failed to initialize camera offsets, recieved: {init.frame_counts()}, minimum frames: {self.config.init_window}")

      return offsets

  def create_sync(self):
    has_latching = all([info.has_latching for info in self.camera_info.values()])

    if has_latching:
      timestamp_offsets = self.camera_set.compute_clock_offsets(self.query_time)
    else:
      timestamp_offsets = self.initialize_offsets()

    now = self.query_time()
    for camera, offset in timestamp_offsets.items():
      date = datetime.fromtimestamp(now - offset)
      self.logger.info(f"Camera {camera} clocks {date.strftime('%M:%S.%f')}")

    self.sync_handler = SyncHandler(time_offsets=timestamp_offsets,
                                    sync_threshold=self.config.sync_threshold_msec / 1000.,
                                    sync_timeout=self.config.timeout_msec / 1000.,

                                    process_buffer = self._process_buffer,
                                    query_time=self.query_time, 
                                    logger=self.logger,
                                    num_workers=self.config.sync_workers)    

    self.sync_handler.bind(on_group=self.processor.process_image_set)


  def start(self):
    if self.is_started:
      self.logger.info("Camera pipeline already started")
      return 

    self.logger.info("Starting camera pipeline")

    try:
      resync_time = self.query_time() - self.config.resync_offset_sec
      if self.sync_handler is None or self.sync_handler.most_recent_frame < resync_time:
        self.create_sync()

      self.camera_set.bind(on_buffer=self.sync_handler.push_image)

      if not self.camera_set.is_started:
        self.camera_set.start()
      self.logger.info("Started camera pipeline")
    except Exception as e:
      raise e
  

    
  @property
  def is_started(self):
    return self.camera_set.is_started

  def stop(self):
    if not self.is_started:
      self.logger.info("Camera pipeline already stopped")
      return 
      
    self.logger.info("Stopping camera pipeline")

    self.camera_set.unbind_cameras()
    self.camera_set.unbind(self.sync_handler.push_image)

    self.sync_handler.flush()

    self.camera_set.stop()
    self.logger.info("Stopped camera pipeline")
    self.emit("on_stopped")


  def release(self):
    self.stop()

    self.processor.stop()
    del self.camera_set

    self.manager.release()
    del self.manager

    self.logger.info("Stopping taichi queue...")
    TaichiQueue.stop()

    self.logger.info("Pipeline release done")


