import warnings
from ids_peak import ids_peak
from ids_peak import ids_peak_ipl_extension

import numpy as np
import torch

from camera_driver.image import CameraImage, camera_encodings



class Buffer():
  def __init__(self, camera_name:str, buffer:ids_peak.Buffer):

    self.camera_name = camera_name
    self._buffer = buffer

  def image(self, device:torch.device) -> CameraImage:
    img = ids_peak_ipl_extension.BufferToImage(self._buffer)
    arr = np.frombuffer(img.DataView(), count=img.ByteCount(), dtype=np.uint8)

    with warnings.catch_warnings():
      warnings.simplefilter("ignore", category=UserWarning)
      return CameraImage(
        self.camera_name,
        image_data = torch.from_numpy(arr).to(device=device, non_blocking=True),

        timestamp_ns=self._buffer.Timestamp_ns(),
        offset_ns = 0,
        
        image_size = (img.Width(), img.Height()),
        encoding = camera_encodings[img.PixelFormat().Name()]
      )

  def release(self):
    self._buffer.ParentDataStream().QueueBuffer(self._buffer)
