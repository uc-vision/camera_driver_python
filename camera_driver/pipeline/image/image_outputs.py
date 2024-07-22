
from dataclasses import dataclass
import threading
from beartype.typing import  Optional
from beartype import beartype
from functools import cached_property

from nvjpeg_torch import Jpeg

from camera_geometry import Camera
from taichi_image import interpolate

import torch 

from camera_driver.concurrent.taichi_queue import TaichiQueue
from camera_driver.pipeline.config import ImageSettings

from .camera_image import CameraImage

local_jpeg = threading.local()

def jpeg():

  if not hasattr(local_jpeg, "encoder"):
    local_jpeg.encoder = Jpeg()
  return local_jpeg.encoder


@beartype
@dataclass
class ImageOutputs(object):
    
  raw:CameraImage
  
  rgb:torch.Tensor
  settings : ImageSettings
  calibration:Optional[Camera] = None

  def __repr__(self):
    h, w, c = self.rgb.shape

    calibrated = "uncalibrated" if self.calibration is None else "calibrated"
    return f"ImageOutputs({self.raw.camera_name}, {w}x{h}x{c} {calibrated}, {self.rgb.device})"

  def encode(self, image:torch.Tensor):
    encoder = jpeg()  
    return encoder.encode(image,
                          quality=self.settings.jpeg_quality,
                          input_format=Jpeg.RGBI).numpy().tobytes()
  
      
  @property
  def camera_name(self) -> str:
    return self.raw.camera_name
  
  @property
  def timestamp_sec(self) -> float:
    return self.raw.timestamp_sec 

  @cached_property
  def compressed(self) -> bytes:    
    return self.encode(self.rgb)

  @cached_property
  def preview(self) -> torch.Tensor:
    return TaichiQueue.run_sync(interpolate.resize_width, self.rgb, self.settings.preview_size)

  @cached_property
  def compressed_preview(self) -> bytes:
    return self.encode(self.preview)
  
  @property
  def camera_name(self) -> str:
    return self.raw.camera_name
  

  @property
  def camera(self) -> Camera:
    height, width, _ = self.rgb.shape

    if self.calibration is not None:  
      if self.calibration.width != width or self.calibration.height != height:
        calibration = self.calibration.resize_image( (width, height) )
        
    return calibration




