from dataclasses import dataclass
from beartype.typing import  Optional, Tuple
import warnings
from beartype import beartype

import numpy as np
import torch

from camera_driver.data import ImageEncoding, Timestamped
from camera_geometry import Camera

from camera_driver.driver.interface import Buffer



@beartype
@dataclass
class CameraImage(Timestamped):
  image_data: torch.Tensor

  image_size: Tuple[int, int]
  encoding: ImageEncoding

  @property
  def device(self):
    return self.image_data.device

  def __repr__(self):
    w, h = self.image_size
    return f"CameraImage({self.camera_name}, {w}x{h}, {str(self.image_data.dtype)}, {self.encoding.value}, {self.stamp_pretty})"

  @staticmethod
  def from_buffer(buffer:Buffer, clock_time_sec:float, device:torch.device):
    """ Convert buffer to CameraImage
        Image is copied to torch Tensor and uploaded to device """

    torch_image = numpy_torch(buffer.image_data, device)
    return CameraImage(timestamp_sec=buffer.timestamp_sec,
                      clock_time_sec=clock_time_sec,
                      camera_name=buffer.camera_name,
                      image_data = torch_image,
                      image_size=buffer.image_size,
                      encoding=buffer.encoding)
                       


def numpy_torch(arr:np.array, device=torch.device("cpu")):
  """ Convert numpy array to torch tensor (ignoring warnings from non-writable numpy arrays) """
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

  throughput_mb : Tuple[float, float] 
  model : str 

  calibration : Optional[Camera] = None

  def __repr__(self):    
    w, h = self.image_size
    t, t_max = self.throughput_mb
    return f"CameraInfo({self.name}:{self.serial} {self.model} {w}x{h} {self.encoding} {t:.1f}/{t_max:.1f}MB/s)"
