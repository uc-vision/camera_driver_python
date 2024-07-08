from dataclasses import dataclass
from datetime import datetime
from typing import  Tuple
import warnings
from beartype import beartype

import numpy as np
import torch
from .encoding import ImageEncoding



@beartype
@dataclass
class CameraImage:
  camera_name: str
  image_data: torch.Tensor

  timestamp_sec: float
  offset_sec: float

  image_size: Tuple[int, int]
  encoding: ImageEncoding

  def __repr__(self):
    date = datetime.fromtimestamp(self.timestamp_sec)
    pretty_time = date.strftime("%H:%M:%S.%f")
    w, h = self.image_size

    return f"CameraImage({self.camera_name}, {w}x{h}, {self.image_data.shape[0]}:{str(self.image_data.dtype)}, {self.encoding.value}, {pretty_time})"



def numpy_image(arr:np.array, device=torch.device("cpu")):
  with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=UserWarning)
    return torch.from_numpy(arr).to(device=device, non_blocking=True)
