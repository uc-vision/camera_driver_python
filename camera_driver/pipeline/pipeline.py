from dataclasses import replace
import logging
from typing import Set
from beartype.typing import Dict

import torch
from beartype import beartype
from pydispatch import Dispatcher

from camera_driver.camera_group.camera_set import CameraSet
from camera_driver.camera_group.sync_handler import SyncHandler, TimeQuery
from camera_driver.driver.interface import Buffer, Camera

from .config import CameraPipelineConfig, ImageSettings
from .image.camera_image import CameraImage, CameraInfo
from .image.frame_processor import FrameProcessor
from .image.image_outputs import ImageOutputs

from camera_driver.concurrent.taichi_queue import TaichiQueue

def missing_cameras(serials:Set[str], requred:Dict[str, str]):
  return 

@beartype
def cameras_from_config(config:CameraPipelineConfig, logger:logging.Logger):

  manager = config.backend.create(config.camera_settings, logger)
  logger.info(f"Found cameras {manager.camera_serials()}")

  missing = {name:serial for name, serial in config.camera_serials.items() if serial not in manager.camera_serials()}
  if len(missing) > 0:
    raise ValueError(f"Camera(s) not found: {missing}")

  if config.reset_cycle is True:
    manager.reset_cameras(manager.camera_serials())
    cameras = manager.wait_for_cameras(config.camera_serials)

  else:
    cameras = {name:manager.init_camera(name, serial)
            for name, serial in config.camera_serials.items()}

  for k, camera in cameras.items():
    camera.setup_mode("master" if k == config.master else "slave")
    camera.update_properties(config.parameters.camera_properties)
    
  return cameras, manager

def get_camera_info(name:str, camera:Camera):
  return CameraInfo(
    name=name,
    serial=camera.serial,
    image_size=camera.image_size,
    encoding=camera.encoding,
  )


class CameraPipeline(Dispatcher):
  _events_ = ["on_image_set", "on_stopped", "on_settings"]

  @beartype
  def __init__(self, config:CameraPipelineConfig, 
               logger:logging.Logger, 
               query_time:TimeQuery):
    
    self.config = config
    self.query_time = query_time

    cameras, manager = cameras_from_config(config, logger)
    self.camera_set = CameraSet(cameras, logger, master=config.master)

    self.sync_handler = None
    self.manager = manager
    self.logger = logger

    self.camera_info = {name:get_camera_info(name, camera) for name, camera in cameras.items()}
    self.processor = FrameProcessor(self.camera_info, settings=config.parameters, 
                                    logger=logger, device=torch.device(config.device))
  

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


  def start(self):
    if self.is_started:
      self.logger.info("Camera pipeline already started")
      return 

    self.logger.info("Starting camera pipeline")
    timestamp_offsets = self.camera_set.compute_clock_offsets(self.query_time)

    self.sync_handler = SyncHandler(time_offsets=timestamp_offsets,
                                    sync_threshold=self.config.sync_threshold_msec / 1000.,
                                    sync_timeout=self.config.timeout_msec / 1000.,

                                    process_buffer = self._process_buffer,
                                    query_time=self.query_time, 
                                    logger=self.logger)    

    self.sync_handler.bind(on_group=self.processor.process_image_set)

    self.camera_set.bind(on_buffer=self.sync_handler.push_image)
    self.camera_set.start()
    self.logger.info("Started camera pipeline")

    
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
    self.sync_handler = None

    self.camera_set.stop()
    self.emit("on_stopped")
    self.logger.info("Stopped camera pipeline")


  def release(self):
    self.stop()

    self.processor.stop()
    self.manager.release()
    TaichiQueue.stop()
