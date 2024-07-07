
from logging import Logger
from typing import Dict, List

import PySpin
from .camera import Camera
from . import helpers


class Manager:
    def __init__(self, logger:Logger):

      self.logger = logger
      self.system = PySpin.System.GetInstance()

  
    def _device_dict(self) -> Dict[str, PySpin.CameraPtr]:
      camera_list = self.system.GetCameras()
      return {helpers.get_camera_serial(camera): camera for camera in camera_list}


    def camera_serials(self) -> List[str]:
      return list(self._device_dict().keys())

    
    def init_camera(self, name:str, serial:str) -> Camera:
      camera = self._device_dict()[serial]
      return Camera(name, camera, logger=self.logger)
    

    def reset_cameras(self):
      camera = self._device_dict()
      for camera in camera.values():
        helpers.reset_camera(camera)
      


    def release(self):
        self.system.ReleaseInstance()
