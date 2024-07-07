
from logging import Logger
import logging
from typing import  Dict, List
import PySpin

from beartype import beartype
from pydispatch import Dispatcher
from .buffer import Buffer

from . import helpers

SettingList = List[Dict]
Settings = Dict[str, SettingList]


class ImageEventHandler(PySpin.ImageEventHandler):
  def __init__(self, on_image):
    super(ImageEventHandler, self).__init__()
    self.on_image = on_image

  def OnImageEvent(self, image):
    self.on_image(image)


class Camera(Dispatcher):
  _events_ = ["on_started", "on_image"]

  @beartype
  def __init__(self, name:str, camera:PySpin.CameraPtr, logger:Logger):
    self.camera = camera

    camera.Init()
    self.nodemap = camera.GetNodeMap()
    self.transport = camera.GetTLDeviceNodeMap()

    self.logger = logger
    self.name = name

    self.handler = None

  @beartype
  def load_config(self, config:Settings, mode:str="slave"):

    self.log(logging.INFO, f"Loading camera configuration ({mode})...")
    helpers.load_defaults(self.camera)

    self.set_value("TLParamsLocked", 0)
    self._set_settings(self.transport, config['transport_layer'])
    self.set_value("TLParamsLocked", 1)

    self._set_settings(self.nodemap, config['device'])
    self._set_settings(self.nodemap, config[mode])


  def _set_settings(self, nodemap, config:Dict[str, Dict]):
    for setting in config:
        setting_name, value = helpers.dict_item(setting)
        self.log(logging.INFO, f"Setting {setting_name} to {value}")

        try:
          helpers.set_value(nodemap, setting_name, value)
        except helpers.NodeException as e:
          self.log(logging.WARNING, f"Failed to set {setting_name} to {value}: {e}")


  def get_value(self, node_name:str):
    return helpers.get_value(self.nodemap, node_name)

  def set_value(self, node_name:str, value:int):
    helpers.set_value(self.nodemap, node_name, value)


  def log(self, level:int, message:str):
    self.logger.log(level, f"{self.name}:{message}")

  def _image_event(self, image):
    self.emit("on_image", Buffer(self.name, image))

  @property
  def started(self):
    return self.handler is not None
    
  def start(self):
    assert not self.started, f"Camera {self.name} is already started"
    self.logger.info("{self.name}:Starting camera capture...")

    self.handler = ImageEventHandler(self._image_event)
    self.camera.RegisterEventHandler(self.handler)    

    self.camera.BeginAcquisition()
    if helpers.validate_streaming(self.camera):
      raise RuntimeError(f"Camera {self.name} did not begin streaming")

    self.log(logging.INFO, "started.")

    self.emit("on_started", True)
    self.capture_thread.start()

  def stop(self):
    assert self.started, f"Camera {self.name} is not started"
    self.logger.info(f"{self.name}:Stopping camera capture...")

    self.camera.UnregisterEventHandler(self.handler)    
    self.camera.EndAcquisition()

    self.log(logging.INFO, "stopped.")

    self.emit("on_started", False)

  def release(self):
    if self.started:
      self.stop()

    self.camera.DeInit()