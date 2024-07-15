from dataclasses import replace
import logging
from typing import Dict

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


@beartype
def cameras_from_config(config:CameraPipelineConfig, logger:logging.Logger):

  manager = config.backend.create(logger)
  logger.info(f"Found cameras {manager.camera_serials()}")

  cameras_required = set(config.camera_serials.values())
  if cameras_required > manager.camera_serials():
    raise ValueError(f"Camera(s) not found: {cameras_required - manager.camera_serials()}")

  if config.reset_cycle is True:
    manager.reset_cameras(manager.camera_serials())
    cameras = manager.wait_for_cameras(config.cameras)

  else:
    cameras = {name:manager.init_camera(name, serial)
            for name, serial in config.cameras.items()}
  
  for camera in cameras.values():
    camera.load_config(config.camera_settings, 
                      "master" if camera.name == config.master else "slave")
    
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
               camera_settings:Dict[str, Dict], 
               logger:logging.Logger, 
               query_time:TimeQuery):
    
    self.config = config
    self.query_time = query_time

    cameras, manager = cameras_from_config(config, camera_settings, logger)
    self.camera_set = CameraSet(cameras, logger, master=config.master)

    self.camera_set.update_properties(
      config.parameters.camera_properties)

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
    return CameraImage.from_buffer(buffer, self.processor.device)


  def update_settings(self, image_settings:ImageSettings):
    self.processor.update_settings(image_settings)
    self.camera_set.update_properties(image_settings.camera_properties)

    self.config = replace(self.config, parameters=image_settings)
    self.emit("on_settings", image_settings)


  def start(self):
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
    assert self.is_started, "Camera pipeline not started"
    self.logger.info("Stopping camera pipeline")

    self.processor.stop()

    self.camera_set.release()
    self.sync_handler.flush()
    self.sync_handler = None

    self.emit("on_stopped")
    self.logger.info("Stopped camera pipeline")


  def release(self):
    if self.is_started:
      self.stop()

    self.manager.release()
    TaichiQueue.stop()
