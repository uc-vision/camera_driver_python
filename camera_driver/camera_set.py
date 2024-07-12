import logging
from typing import Callable, Dict

from beartype import beartype

from camera_driver.sync.sync_handler import TimeQuery

from .camera_interface  import Buffer, Camera
from pydispatch import Dispatcher


class CameraSet(Dispatcher):
  _events_ = ["on_buffer"]


  def __init__(self, 
               cameras:Dict[str, Camera], 
               logger:logging.Logger):

    self.is_started = False
    self.cameras = cameras

    self.logger = logger

  @beartype
  def compute_clock_offsets(self, get_timestamp:TimeQuery):
    return {name:camera.compute_clock_offset(get_timestamp) 
                  for name, camera in self.cameras.items()}
  
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

