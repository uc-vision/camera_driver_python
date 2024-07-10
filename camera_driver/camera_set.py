import logging
from typing import Dict, Tuple

from .camera_interface  import Buffer, Camera, create_manager, Manager
from pydispatch import Dispatcher


class CameraSet(Dispatcher):
  _events_ = ["on_buffer"]
  

  def __init__(self, 
               
               manager:Manager, 
               cameras:Dict[str, Camera], 
               logger:logging.Logger):

    self.started = False
    self.cameras = cameras
    self.manager = manager

    self.logger = logger


  @staticmethod
  def from_config(logging:logging.Logger, config:dict, camera_settings:dict) -> Tuple[Dict[str, Camera], Manager]:

    manager = create_manager(camera_settings["backend"], logging)
    logging.info(f"Found cameras {manager.camera_serials()}")

    if config["reset_cycle"] is True:
      manager.reset_cameras(manager.camera_serials())
    
    cameras_required = set(config["cameras"].values())
    if cameras_required > manager.camera_serials():
      raise ValueError(f"Camera(s) not found: {cameras_required - manager.camera_serials()}")
    
    cameras = {name:manager.init_camera(name, serial) 
              for name, serial in config["cameras"].items()}
    
    master = camera_settings.get("master", None)

    for camera in cameras.values():
      camera.load_config(camera_settings["camera_settings"], 
                        "master" if camera.name == master else "slave")

    return CameraSet(manager, cameras, logging)


  def compute_clock_offsets(self, get_timestamp):
    return {name:camera.compute_clock_offset(get_timestamp) 
                  for name, camera in self.cameras.items()}
  
  def __repr__(self):
    cameras = ", ".join([f"{name}:{camera.serial}" for name, camera in self.cameras.items()])
    return f"CameraSet({cameras})"

  @property
  def camera_ids(self):
    return set(self.cameras.keys())
  

  def on_buffer(self, buffer:Buffer):
    self.dispatch("on_buffer", buffer)


  def start(self):
    assert not self.started

    for k, camera in self.cameras.items():
      camera.bind(on_buffer = self.on_buffer)
      camera.start()

    self.started = True

  def stop(self):
    assert not self.started

    for k, camera in self.cameras.items():
      camera.unbind(self.on_buffer)
      camera.stop()

    self.started = True


  def release(self):
    for _, camera in self.cameras.items():
      camera.release()

    del self.cameras
    self.manager.release()