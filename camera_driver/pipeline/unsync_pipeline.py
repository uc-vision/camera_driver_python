from dataclasses import replace
import logging
from beartype.typing import Dict

from camera_driver.pipeline.pipeline import cameras_from_config
import torch
from beartype import beartype
from pydispatch import Dispatcher

from camera_driver.camera_group.camera_set import CameraSet
from camera_driver.camera_group.sync_handler import TimeQuery
from camera_driver.driver.interface import Buffer

from .config import CameraPipelineConfig, ImageSettings
from .image.camera_image import CameraImage
from .image.frame_processor import FrameProcessor
from .image.image_outputs import ImageOutputs

from camera_driver.concurrent.taichi_queue import TaichiQueue



class CameraPipelineUnsync(Dispatcher):
  _events_ = ["on_image", "on_stopped", "on_settings"]

  @beartype
  def __init__(self, config:CameraPipelineConfig, 
               logger:logging.Logger, 
               query_time:TimeQuery):
    
    self.config = config
    self.query_time = query_time

    cameras, manager = cameras_from_config(config, logger)
    self.camera_set = CameraSet(cameras, logger, master=config.master)

    self.manager = manager
    self.logger = logger

    self.device = torch.device(config.device)

    self.camera_info = {name:camera.camera_info() for name, camera in cameras.items()}

    for info in self.camera_info.values():
      logger.info(str(info))

  
    def frame_processor(k):
      processor = FrameProcessor({k:self.camera_info[k]}, settings=config.parameters, 
                            logger=logger, device=torch.device(config.device), max_size=1, num_workers=1)
      processor.bind(on_frame=self._on_image)
      return processor

    self.processors = {k:frame_processor(k) for k in cameras.keys()}
  

  def _on_image(self, group:Dict[str, ImageOutputs]):
    outputs = list(group.values())[0]
    self.emit("on_image", outputs)
  

  def _process_buffer(self, buffer:Buffer):
    now = self.query_time()
    return CameraImage.from_buffer(buffer, now, self.device)
  
  def _process_image(self, camera_image:CameraImage):
    k = camera_image.camera_name
    self.processors[k].process_image_set({k:camera_image})


  def update_settings(self, image_settings:ImageSettings):
    for processor in self.processors.values():
      processor.update_settings(image_settings)

    if self.is_started:
      self.camera_set.update_properties(image_settings.camera_properties)

    self.config = replace(self.config, parameters=image_settings)
    self.emit("on_settings", image_settings)



  def start(self):
    if self.is_started:
      self.logger.info("Camera pipeline already started")
      return 

    self.logger.info("Starting camera pipeline")
    
    self.camera_set.bind(on_buffer=self._process_image)  
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
    self.camera_set.stop()

    self.logger.info("Stopped camera pipeline")
    self.emit("on_stopped")


  def release(self):
    self.stop()

    for processor in self.processors.values():
      processor.stop()

    self.manager.release()
    TaichiQueue.stop()
