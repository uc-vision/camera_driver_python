from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List
from beartype import beartype

from camera_driver.driver.interface import BackendType, CameraProperties
from omegaconf import OmegaConf

class Transform(Enum):
  none = 0
  rotate_90 = 1
  rotate_180 = 2
  rotate_270 = 3
  transpose = 4
  flip_horiz = 5
  flip_vert = 6
  transverse = 7

  
class ToneMapper(Enum):
  linear = 1
  reinhard = 2


def clamp(x, lower, upper):
  return max(min(x, lower), upper)

@beartype
@dataclass
class ImageSettings:

  # Camera parameters
  exposure: int = 2000
  gain: float = 1.0
  framerate: float = 10.

  # output parameters
  resize_width: int = 0
  preview_size : int = 200
  jpeg_quality : int = 94

  # Tonemapping parameters
  tone_gamma: float = 1.0
  tone_intensity : float = 1.0
  light_adapt : float = 1.0
  color_adapt : float = 1.0

  # Moving average to smooth intensity scaling over time
  moving_average : float = 0.02

  # linear or reinhard
  tone_mapping: ToneMapper = ToneMapper.reinhard   

  # none rotate_90 rotate_180 rotate_270 transpose flip_horiz flip_vert 
  transform : Transform = Transform.none
  
  @property
  def camera_properties(self):
    return CameraProperties(
      exposure=self.exposure, 
      gain=self.gain, 
      framerate=self.framerate)




  @property
  def is_resizing(self):
    return self.resize_width > 0.0

  def __post_init__(self):
    self.preview_size = int(self.preview_size)
    self.jpeg_quality = int(clamp(self.jpeg_quality, 1, 100))


@beartype
@dataclass 
class CameraPipelineConfig:
  backend:BackendType
  camera_serials:Dict[str, str]

  master:Optional[str]
  reset_cycle:bool
  sync_threshold_msec:float
  timeout_msec:float

  device:str

  parameters: ImageSettings
  camera_settings: Dict[str, List]

  @staticmethod
  def load_yaml(filename) -> 'CameraPipelineConfig':
    return load_structured(filename, CameraPipelineConfig)



def load_structured(file, structure):
   conf = OmegaConf.load(file)
   merged = OmegaConf.merge(OmegaConf.structured(structure), conf)

   obj = OmegaConf.to_object(merged)
   return obj


def load_yaml(file):
  return OmegaConf.load(file)
  
  



