
from logging import Logger
from time import sleep
from beartype.typing import Dict, List, Set

from queue import Queue

import PySpin
from .camera import Camera
from . import helpers

from camera_driver.driver import interface


class Manager(interface.Manager):
    def __init__(self, presets:Dict[str, interface.SettingList], logger:Logger):

      self.logger = logger
      self.system = PySpin.System.GetInstance()

      self.presets = presets
  
    def _devices(self) -> Dict[str, PySpin.CameraPtr]:
      camera_list = self.system.GetCameras()
      return {str(helpers.get_camera_serial(camera)): camera for camera in camera_list}


    def camera_serials(self) -> Set[str]:
      return set(self._devices().keys())

    
    def init_camera(self, name:str, serial:str) -> Camera:
      camera = self._devices()[serial]
      return Camera(name, camera, self.presets, logger=self.logger)
    

    def wait_for_cameras(self, cameras:Dict[str, str]):
      queue = Queue(1)
      handler = ResetHandler(on_added=queue.put)

      interfaces = self.system.GetInterfaces()    

      for iface in interfaces:
        iface.RegisterEventHandler(handler)

      by_serial = {serial:k for k, serial in cameras.items()}
      cameras_found = {}
      self.logger.info(f"Waiting for cameras {by_serial}")

      while len(by_serial) > 0:
        camera = queue.get()
        serial = str(helpers.get_camera_serial(camera))
        if serial in by_serial:

          name = by_serial[serial]
          cameras_found[name] = Camera(name, camera, self.presets, self.logger)
          self.logger.info(f"Camera {name}:{serial} found.")

          del by_serial[serial]      

      for iface in interfaces:
        iface.UnregisterEventHandler(handler)

      return cameras_found


    def reset_cameras(self, camera_set:Set[str]):
      assert camera_set <= self.camera_serials(), f"Camera(s) not found {camera_set - self.camera_serials()}"

      cameras = self._devices()
      self.logger.info(f"Resetting {len(cameras)} cameras...")

      for k, camera in cameras.items():
        self.logger.info(f"Resetting {k}")
        helpers.reset_camera(camera)
      
      self.logger.info("Done.")


    def release(self):
        self.logger.info("Releasing Spinnaker instance...")
        self.system.ReleaseInstance()
        self.logger.info("Done.")




class ResetHandler(PySpin.InterfaceEventHandler):
    def __init__(self, on_added):
        super(ResetHandler, self).__init__()      
        self.on_added = on_added

    def OnDeviceArrival(self, camera):
        self.on_added(camera)

    def OnDeviceRemoval(self, camera):
        pass
