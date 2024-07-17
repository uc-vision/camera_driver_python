
from logging import Logger
from typing import Dict, Optional
from beartype import beartype
from beartype.typing import Set

from ids_peak import ids_peak
from .camera import Camera
from camera_driver.driver import interface



class Manager(interface.Manager):
    def __init__(self, presets:Dict[interface.SettingList], logger:Logger):

      self.logger = logger
      self.presets = presets

      ids_peak.Library.Initialize()
      self.devices:Dict[str, ids_peak.DeviceDescriptor] = {}

      # Initialize Harvester
      self.device_manager = ids_peak.DeviceManager.Instance()

      self.found = DeviceFoundCallback(self)
      self.device_manager.RegisterDeviceFoundCallback(self.found)
      self.device_manager.Update()      


    def _open_device(self, serial:str):
      device = self.devices[serial]
      return device.OpenDevice(ids_peak.DeviceAccessType_Control)

    def camera_serials(self) -> Set[str]:
      return set(self.devices.keys())

    @beartype
    def reset_cameras(self, camera_set:Optional[Set[str]]=None):

      if camera_set is None:
        camera_set = self.camera_serials()

      assert camera_set <= self.camera_serials(), f"Camera(s) not found {camera_set - self.camera_serials()}"      
      devices = self.devices
      self.devices = {}

      for serial, desc in devices.items():
        self.logger.info(f"Resetting camera {serial}")

        device =  desc.OpenDevice(ids_peak.DeviceAccessType_Control)
        nodemap = device.RemoteDevice().NodeMaps()[0]

        node = nodemap.FindNode("DeviceReset")
        node.Execute()
        node.WaitUntilDone()

      self.device_manager.Update()



    def init_camera(self, name:str, serial:str) -> Camera:
      assert serial in self.devices, f"Camera {serial} not found"

      desc = self.devices[serial]
      return Camera(name, desc.OpenDevice(ids_peak.DeviceAccessType_Control), self.presets, logger=self.logger)


    def wait_for_cameras(self, cameras:Dict[str, str]) -> interface.Dict[str, interface.Camera]:
      by_serial = {serial:k for k, serial in cameras.items()}
      self.logger.info(f"Waiting for cameras {by_serial}")

      while set(self.devices.keys())  < set(cameras.values()):
        self.device_manager.Update()

      return {name:self.init_camera(name, serial) for name, serial in cameras.items()}


    def release(self):
       ids_peak.Library.Close()


class DeviceFoundCallback(ids_peak.DeviceManagerDeviceFoundCallbackBase):
  def __init__(self, manager:'Manager'):
    super(DeviceFoundCallback, self).__init__()
    self.manager = manager

  def call(self, device:ids_peak.DeviceDescriptor):
    print(f"Device found {device.SerialNumber()}")
    self.manager.devices[device.SerialNumber()] = device