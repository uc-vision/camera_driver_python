
from logging import Logger
from typing import Set

from ids_peak import ids_peak
from .camera import Camera
from camera_driver import camera_interface


class Manager(camera_interface.Manager):
    def __init__(self, logger:Logger):

      self.logger = logger
      ids_peak.Library.Initialize()

    
      # Initialize Harvester
      self.device_manager = ids_peak.DeviceManager.Instance()
      self.device_manager.Update()      

    def _devices(self):
      devices = self.device_manager.Devices()
      return {device.SerialNumber(): device for device in devices}


    def camera_serials(self) -> Set[str]:
      return set(self._devices().keys())


    def reset_cameras(self, camera_set:Set[str]):
      assert camera_set <= self.camera_serials, f"Camera(s) not found {camera_set - self.camera_serials()}"
      assert False, "Not implemented"


    def init_camera(self, name:str, serial:str) -> Camera:
      device = self._devices()[serial]
      return Camera(name, device.OpenDevice(ids_peak.DeviceAccessType_Control), logger=self.logger)