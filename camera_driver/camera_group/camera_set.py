from functools import cache
import logging
from typing import Set
from beartype.typing import Dict, Optional

from beartype import beartype

from .sync_handler import TimeQuery

from camera_driver.driver.interface  import Buffer, Camera, CameraProperties
from pydispatch import Dispatcher


class CameraSet(Dispatcher):
  _events_ = ["on_buffer"]

  def __init__(self, 
               cameras:Dict[str, Camera], 
               logger:logging.Logger,
               master:Optional[str] = None):

    self.is_started = False
    self.cameras = cameras

    self.logger = logger
    self.master = master


  @beartype
  def compute_clock_offsets(self, get_timestamp:TimeQuery):
    assert self.has_latching, "Cannot compute clock offsets without timestamp latch support"

    return {name:camera.compute_clock_offset(get_timestamp) 
                  for name, camera in self.cameras.items()}
  
  @property
  def has_latching(self):
    return all([camera.has_latching for camera in self.cameras.values()])

  def __repr__(self):
    cameras = ", ".join([f"{name}:{camera.serial}" for name, camera in self.cameras.items()])
    return f"CameraSet({cameras})"

  @property
  def camera_ids(self):
    return set(self.cameras.keys())
  

  def on_buffer(self, buffer:Buffer):
    self.emit("on_buffer", buffer)


  def start(self):
    assert not self.is_started, "CameraSet already started"

    for k, camera in self.cameras.items():
      camera.bind(on_buffer = self.on_buffer)
      camera.start()

    self.is_started = True

  def unbind_cameras(self):
    for k, camera in self.cameras.items():
      camera.unbind(self.on_buffer)



  def stop(self):
    assert self.is_started, "CameraSet not started"

    for k, camera in self.cameras.items():
      camera.unbind(self.on_buffer)
      camera.stop()

    self.is_started = False


  def release(self):
    if self.is_started:
      self.stop()

    for _, camera in self.cameras.items():
      camera.release()

  @cache
  def log_once(self, level:int, message:str):
    self.logger.log(level, message)


  def update_properties(self, settings:CameraProperties):
    for camera in self.cameras.values():
      camera.update_properties(settings) 
