from dataclasses import dataclass, replace
from datetime import datetime
from typing import  Optional, Tuple
import warnings
from beartype import beartype

import numpy as np
import torch
from .encoding import ImageEncoding

from camera_geometry import Camera


@beartype
@dataclass
class CameraImage:
  camera_name: str
  image_data: torch.Tensor

  timestamp_sec: float

  image_size: Tuple[int, int]
  encoding: ImageEncoding


  @property
  def device(self):
    return self.image_data.device



  @property
  def datetime(self):
    return datetime.fromtimestamp(self.timestamp_sec)
  
  @property
  def stamp_pretty(self):
    return self.datetime.strftime('%M%S.3f')

  def with_timestamp(self, timestamp_sec:float):
    return replace(self, timestamp_sec=timestamp_sec)

  def __repr__(self):
    w, h = self.image_size

    return f"CameraImage({self.camera_name}, {w}x{h}, {self.image_data.shape[0]}:{str(self.image_data.dtype)}, {self.encoding.value}, {self.stamp_pretty})"



def numpy_image(arr:np.array, device=torch.device("cpu")):
  with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=UserWarning)
    return torch.from_numpy(arr).to(device=device, non_blocking=True)


@beartype
@dataclass
class CameraInfo:
  name : str

  serial:str
  
  image_size:Tuple[int, int]
  encoding : ImageEncoding

  calibration : Optional[Camera] = None

  def __repr__(self):    
    w, h = self.image_size
    return f"CameraInfo({self.name}:{self.serial} {w}x{h} {self.encoding})"
