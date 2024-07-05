
from logging import Logger
from typing import List

from ids_peak import ids_peak
from .camera import Camera

class Manager:
    def __init__(self, logger:Logger):

      self.logger = logger
      ids_peak.Library.Initialize()

    
      # Initialize Harvester
      self.device_manager = ids_peak.DeviceManager.Instance()
      self.device_manager.Update()      

    def _device_dict(self):
      devices = self.device_manager.Devices()
      return {device.SerialNumber(): device for device in devices}


    def camera_serials(self) -> List[str]:
      return list(self._device_dict().keys())



    def init_camera(self, name:str, serial:str) -> Camera:
      device = self._device_dict()[serial]
      return Camera(name, device.OpenDevice(ids_peak.DeviceAccessType_Control), logger=self.logger)