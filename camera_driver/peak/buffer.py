import warnings
from ids_peak import ids_peak
from ids_peak import ids_peak_ipl_extension

import numpy as np
import torch

from camera_driver.image import CameraImage, camera_encodings
from camera_driver.image.camera_image import numpy_image

from camera_driver import interface


class Buffer(interface.Buffer):
  def __init__(self, camera_name:str, buffer:ids_peak.Buffer):
    assert not buffer.IsIncomplete()

    self.camera_name = camera_name
    self._buffer = buffer

  def image(self, device:torch.device) -> CameraImage:
    img = ids_peak_ipl_extension.BufferToImage(self._buffer)
    arr = np.frombuffer(img.DataView(), count=img.ByteCount(), dtype=np.uint8)

    return CameraImage(
      self.camera_name,
      image_data = numpy_image(arr, device=device),

      timestamp_sec=float(self._buffer.Timestamp_ns()) / 1e9,
      offset_ns = 0.,
      
      image_size = (img.Width(), img.Height()),
      encoding = camera_encodings[img.PixelFormat().Name()]
    )

  def release(self):
    self._buffer.ParentDataStream().QueueBuffer(self._buffer)
    del self._buffer
