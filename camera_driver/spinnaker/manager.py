
from logging import Logger
from time import sleep
from typing import Dict, List, Set

from queue import Queue

import PySpin
from .camera import Camera
from . import helpers

from camera_driver import camera_interface



class Manager(camera_interface.Manager):
    def __init__(self, logger:Logger):

      self.logger = logger
      self.system = PySpin.System.GetInstance()
      
      
  
    def _devices(self) -> Dict[str, PySpin.CameraPtr]:
      camera_list = self.system.GetCameras()
      return {helpers.get_camera_serial(camera): camera for camera in camera_list}


    def camera_serials(self) -> Set[str]:
      return set(self._devices().keys())

    
    def init_camera(self, name:str, serial:str) -> Camera:
      camera = self._devices()[serial]
      return Camera(name, camera, logger=self.logger)
    

    def wait_for_cameras(self, camera_set:Set[str]):
      queue = Queue(1)
      handler = ResetHandler(on_added=queue.put)

      interfaces = self.system.GetInterfaces()    
      for iface in interfaces:
        iface.RegisterEventHandler(handler)

      while len(camera_set) > 0:
        self.logger.debug(f"Waiting for cameras {camera_set}")

        serial = queue.get()
        if serial in camera_set:
          camera_set.remove(serial)
          self.logger.info(f"Camera {serial} found.")

      for iface in interfaces:
        iface.UnregisterEventHandler(handler)


    def reset_cameras(self, camera_set:Set[str]):
      assert camera_set <= self.camera_serials(), f"Camera(s) not found {camera_set - self.camera_serials()}"

      cameras = self._devices()
      self.logger.info(f"Resetting {len(cameras)} cameras...")

      for camera in cameras.values():
        helpers.reset_camera(camera)
      self.wait_for_cameras(set(cameras.keys()))

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
        self.on_added(helpers.get_camera_serial(camera))

    def OnDeviceRemoval(self, camera):
        pass
