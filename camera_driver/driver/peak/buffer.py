from typing import Tuple

from camera_driver.data.encoding import ImageEncoding, camera_encodings
from camera_driver.driver import interface


from ids_peak import ids_peak
from ids_peak import ids_peak_ipl_extension

import numpy as np


class Buffer(interface.Buffer):
  def __init__(self, camera_name:str, buffer:ids_peak.Buffer):
    assert not buffer.IsIncomplete()

    self._camera_name = camera_name
    self._buffer = buffer

  @property
  def camera_name(self) -> str:
    return self._camera_name

  @property
  def image_data(self) -> np.ndarray:
    """ Note this data is invalidated when the image is released, so must be copied."""
    img = ids_peak_ipl_extension.BufferToImage(self._buffer)
    return np.frombuffer(img.DataView(), count=img.ByteCount(), dtype=np.uint8)

  @property
  def image_size(self) -> Tuple[int, int]:
    return (self._buffer.Width(), self._buffer.Height())  
  
  @property
  def timestamp_sec(self) -> float:
    return float(self._buffer.Timestamp_ns()) / 1e9

  @property
  def encoding(self) -> ImageEncoding:
    return camera_encodings[self._buffer.PixelFormat().Name()]

  

  def release(self):
    self._buffer.ParentDataStream().QueueBuffer(self._buffer)
    del self._buffer
