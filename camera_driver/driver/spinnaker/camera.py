
from logging import Logger
import logging
import traceback
from typing import Tuple
from beartype.typing import  Callable, Dict, List
import PySpin

from beartype import beartype
from camera_driver.data.util import dict_item
import numpy as np

from camera_driver.data.encoding import ImageEncoding, camera_encodings
from .buffer import Buffer

from camera_driver.driver import interface

from . import helpers


class ImageEventHandler(PySpin.ImageEventHandler):
  def __init__(self, on_image):
    super(ImageEventHandler, self).__init__()
    self.on_image = on_image

  def OnImageEvent(self, image):
    self.on_image(image)


class Camera(interface.Camera):

  @beartype
  def __init__(self, name:str, camera:PySpin.CameraPtr, presets:Dict[str, interface.SettingList], logger:Logger):
    self.camera = camera

    camera.Init()
    if not helpers.validate_init(camera):
      raise RuntimeError(f"Failed to initialize camera {name}")

    self.logger = logger
    self.name = name

    self.handler = None
    self.presets = presets


  def compute_clock_offset(self, get_time_sec:Callable[[], float]):
    return helpers.camera_time_offset(self.camera, get_time_sec)


  def camera_info(self) -> interface.CameraInfo:
    return interface.CameraInfo(
      name=self.name,
      serial=self.serial,
      image_size=self.image_size,
      encoding=self.encoding,
      model=self.model,
      throughput_mb=self.throughput_mb,

      has_latching=True
    )

  @property
  def image_size(self):
    return helpers.get_image_size(self.camera)
  
  @property
  def encoding(self) -> ImageEncoding:
      pixel_format = helpers.get_value(self.nodemap, "PixelFormat")

      if pixel_format not in camera_encodings:
        raise ValueError(f"Unsupported pixel format {pixel_format}")
      return camera_encodings[pixel_format]
  
  @property
  def throughput_mb(self) -> Tuple[float, float]:
    t = helpers.get_value(self.nodemap, "DeviceLinkCurrentThroughput")
    t_max = helpers.get_value(self.nodemap, "DeviceLinkThroughputLimit")

    return (t / 1e6, t_max / 1e6)
  
  @property
  def model(self) -> str:
    return helpers.get_value(self.nodemap, "DeviceModelName")
  
  @property
  def serial(self) -> str:
    return str(helpers.get_camera_serial(self.camera))
  

  def __repr__(self):
    w, h = self.image_size
    return f"spinnaker.Camera({self.name}:{self.serial} {w}x{h} {self.encoding})"


  @property 
  def nodemap(self):
    return self.camera.GetNodeMap()
  
  @property
  def stream_nodemap(self):
    return self.camera.GetTLStreamNodeMap()

  @beartype
  def setup_mode(self, mode:str="slave"):
    self.log(logging.INFO, f"Loading camera configuration ({mode})...")
    for k in ['stream', 'device', mode]:
        assert k in self.presets, f"presets missing {k}, options are {list(self.presets.keys())}"

    helpers.load_defaults(self.camera)

    self._set_settings(self.stream_nodemap, self.presets['stream'])
    self._set_settings(self.nodemap, self.presets['device'])
    self._set_settings(self.nodemap, self.presets[mode])



  def _set_settings(self, nodemap, config:Dict[str, Dict]):
    for setting in config:
        setting_name, value = dict_item(setting)
        self.log(logging.DEBUG, f"Setting {setting_name} to {value}")

        try:
          helpers.set_value(nodemap, setting_name, value)
        except helpers.NodeException as e:
          self.log(logging.WARNING, f"Failed to set {setting_name} to {value}: {e}")


  def log(self, level:int, message:str):
    self.logger.log(level, f"{self.name}:{message}")

  def _image_event(self, image):
    if image.IsIncomplete():
      self.log(logging.WARNING, "Recieved incomplete buffer")
      image.Release()

    else:
      try:
        self.emit("on_buffer", Buffer(self.name, image))
      except Exception:
        self.log(logging.ERROR, f"Error handling image: {traceback.format_exc()}")


  def update_properties(self, settings:interface.CameraProperties):
    
    if helpers.is_writable(self.nodemap, "AcquisitionFrameRate"):
      helpers.set_float(self.nodemap, "AcquisitionFrameRate", settings.framerate)

    helpers.set_float(self.nodemap, "Gain", settings.gain)
    helpers.set_int(self.nodemap, "ExposureTime", int(settings.exposure))



  @property
  def started(self):
    return self.handler is not None
    
  def start(self):
    assert not self.started, f"Camera {self.name} is already started"
    self.log(logging.INFO, "Starting camera capture...")

    self.handler = ImageEventHandler(self._image_event)
    self.camera.RegisterEventHandler(self.handler)    

    self.camera.BeginAcquisition()
    if not helpers.validate_streaming(self.camera):
      raise RuntimeError(f"Camera {self.name} did not begin streaming")

    self.log(logging.INFO, "started.")

    self.emit("on_started", True)

  def stop(self):
    assert self.started, f"Camera {self.name} is not started"
    self.logger.info(f"{self.name}:Stopping camera capture...")

    self.camera.UnregisterEventHandler(self.handler)    
    self.handler = None
    
    self.camera.EndAcquisition()

    self.log(logging.INFO, "stopped.")
    self.emit("on_started", False)

  def release(self):
    if self.started:
      self.stop()

    self.camera.DeInit()
    self.camera = None
