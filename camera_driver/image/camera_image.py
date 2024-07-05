from dataclasses import dataclass
from datetime import datetime
from typing import  Tuple
from beartype import beartype

import torch
from .encoding import ImageEncoding



@beartype
@dataclass
class CameraImage:
  camera_name: str
  image_data: torch.Tensor

  timestamp_ns: int
  offset_ns: int

  image_size: Tuple[int, int]
  encoding: ImageEncoding

  def __repr__(self):
    date = datetime.fromtimestamp(self.timestamp_ns / 1e9)
    pretty_time = date.strftime("%H:%M:%S.%f")
    w, h = self.image_size

    return f"CameraImage({self.camera_name}, {w}x{h}, {self.image_data.shape[0]}:{str(self.image_data.dtype)}, {self.encoding.value}, {pretty_time})"
