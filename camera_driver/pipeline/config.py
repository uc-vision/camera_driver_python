from dataclasses import dataclass, field
from enum import Enum
from beartype.typing import Dict, Optional, List
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
  linear = 0
  reinhard = 1


def clamp(x, lower, upper):
  return min(max(x, lower), upper)

@beartype
@dataclass
class ImageSettings:

  # Camera parameters
  exposure: int = field(default=2000, metadata=dict(description="Exposure", min=100, max=20000, step=100))
  gain: float = field(default=1.0, metadata=dict(description="Gain", min=0.0, max=27.0))
  framerate: float = field(default=10.0, metadata=dict(description="Framerate", min=1.6, max=23.0))

  # output parameters
  resize_width: int = field(default=0, metadata=dict(description="Resize width", min=0, max=4096))
  preview_size : int = field(default=200, metadata=dict(description="Preview width", min=64, max=1024))
  jpeg_quality : int = field(default=94, metadata=dict(description="JPEG quality", min=1, max=100))

  # Tonemapping parameters
  tone_gamma: float = field(default=1.0, metadata=dict(description="Gamma", min=0.1, max=5.0))
  tone_intensity : float = field(default=1.0, metadata=dict(description="Intensity", min=0.1, max=5.0))
  light_adapt : float = field(default=1.0, metadata=dict(description="Light adaptation", min=0.0, max=1.0))
  color_adapt : float = field(default=1.0, metadata=dict(description="Color adaptation", min=0.0, max=1.0))

  # Moving average to smooth intensity scaling over time
  moving_average : float = field(default=0.02, metadata=dict(description="Tonemap moving average", min=0.0, max=1.0))

  # linear or reinhard
  tone_mapping: ToneMapper = field(default=ToneMapper.reinhard, metadata=dict(description="Tonemapping algorithm"))

  # none rotate_90 rotate_180 rotate_270 transpose flip_horiz flip_vert 
  transform : Transform = field(default=Transform.none, metadata=dict(description="Image transform"))
  
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
@dataclass(kw_only=True, frozen=True)
class CameraPipelineConfig:
  backend:BackendType
  camera_serials:Dict[str, str]

  master:Optional[str] 
  default_mode:str = 'slave'
  reset_cycle:bool = True

  sync_threshold_msec:float = 10.0
  timeout_msec:float = 2000.0

  init_window:int = 5
  init_timeout_msec:float = 5000.0

  resync_offset_sec:float = 600.0 # 10 minutes
  device:str = 'cuda'

  process_workers:int = 4
  sync_workers:int = 1

  parameters: ImageSettings
  camera_settings: Dict[str, List]

  @staticmethod
  def load_yaml(*filenames:str) -> 'CameraPipelineConfig':
    return load_structured(CameraPipelineConfig, *filenames)



def load_structured(structure, *files:str):
   config = OmegaConf.structured(structure)

   for file in files:
     config = OmegaConf.merge(config, OmegaConf.load(file))

   return OmegaConf.to_object(config)


def load_yaml(file):
  return OmegaConf.load(file)
  
  



