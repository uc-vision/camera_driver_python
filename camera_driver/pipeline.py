

import logging
from typing import Dict

from camera_driver.camera_interface import create_manager
from camera_driver.camera_set import CameraSet
from camera_driver.config import CameraPipelineConfig
from camera_driver.image.camera_image import CameraImage
from camera_driver.sync.sync_handler import SyncHandler, TimeQuery


def cameras_from_config(config:CameraPipelineConfig, camera_settings:Dict[str, Dict], logger:logging.Logger):

  manager = create_manager(config.backend, logger)
  logger.info(f"Found cameras {manager.camera_serials()}")

  cameras_required = set(config.cameras.values())
  if cameras_required > manager.camera_serials():
    raise ValueError(f"Camera(s) not found: {cameras_required - manager.camera_serials()}")

  if config.reset_cycle is True:
    manager.reset_cameras(manager.camera_serials())
    cameras = manager.wait_for_cameras(config.cameras)

  else:
    cameras = {name:manager.init_camera(name, serial)
            for name, serial in config.cameras.items()}
  
  for camera in cameras.values():
    camera.load_config(camera_settings["camera_settings"], 
                      "master" if camera.name == config.master else "slave")
    
  return cameras, manager



class CameraPipeline:

  def __init__(self, config:CameraPipelineConfig, camera_settings:Dict[str, Dict], logger:logging.Logger, query_time:TimeQuery):
    self.config = config
    self.query_time = query_time

    cameras, manager = cameras_from_config(config, camera_settings, logger)
    self.camera_set = CameraSet(cameras, logger)

    self.sync_handler = None
    self.manager = manager
    self.logger = logger
    

  def on_image_set(self, group:Dict[str, CameraImage]):
    print(group)
  

  def start(self):
    self.logger.info("Starting camera pipeline")
    self.sync_handler = SyncHandler(offsets=self.camera_set.compute_clock_offsets(),
                                    sync_threshold=self.config.sync_threshold_msec / 1000.,
                                    sync_timeout=self.config.timeout_msec / 1000.,

                                    query_time=self.query_time, 
                                    device=self.config.device,
                                    logger=self.logger)    


    self.sync_handler.bind("on_group", self.on_image_set)

    self.camera_set.bind(on_buffer=self.sync_handler.push_image)
    self.camera_set.start()
    self.logger.info("Started camera pipeline")

    
  @property
  def is_started(self):
    return self.camera_set.is_started

  def stop(self):
    assert self.is_started, "Camera pipeline not started"
    self.logger.info("Stopping camera pipeline")

    self.camera_set.release()
    self.sync_handler.flush()
    self.sync_handler = None

    self.logger.info("Stopped camera pipeline")


  def release(self):
    if self.is_started:
      self.stop()

    self.manager.release()
