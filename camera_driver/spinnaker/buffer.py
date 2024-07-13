import numpy as np
import PySpin

from camera_driver import interface
from camera_driver.data.encoding import ImageEncoding


pyspin_encoding = {
  PySpin.PixelFormat_BayerRG8: ImageEncoding.Bayer_RGGB8,
  PySpin.PixelFormat_BayerRG12p: ImageEncoding.Bayer_RGGB12,
  PySpin.PixelFormat_BayerRG16: ImageEncoding.Bayer_RGGB16,
  PySpin.PixelFormat_BayerGR8: ImageEncoding.Bayer_GRBG8,
  PySpin.PixelFormat_BayerGR12p: ImageEncoding.Bayer_GRBG12,
  PySpin.PixelFormat_BayerGR16: ImageEncoding.Bayer_GRBG16,
  PySpin.PixelFormat_BayerGB8: ImageEncoding.Bayer_GBRG8,
  PySpin.PixelFormat_BayerGB12p: ImageEncoding.Bayer_GBRG12,
  PySpin.PixelFormat_BayerGB16: ImageEncoding.Bayer_GBRG16,
  PySpin.PixelFormat_BayerBG8: ImageEncoding.Bayer_BGGR8,
  PySpin.PixelFormat_BayerBG12p: ImageEncoding.Bayer_BGGR12,
  PySpin.PixelFormat_BayerBG16: ImageEncoding.Bayer_BGGR16,
}



class Buffer(interface.Buffer):
  def __init__(self, camera_name:str, image:PySpin.Image):
    assert not image.IsIncomplete()

    self._camera_name = camera_name
    self._image = image


  @property
  def camera_name(self) -> str:
    return self._camera_name
  
  @property
  def image_data(self):
    """ Note this data is invalidated when the image is released, so must be copied."""
    return self._image.GetData().view(np.uint8)

  @property
  def image_size(self):
    return (self._image.GetWidth(), self._image.GetHeight())

  @property
  def timestamp_sec(self):
    return float(self._image.GetTimeStamp()) / 1e9

  @property
  def encoding(self):
    pixel_format = self._image.GetPixelFormat()
    if pixel_format not in pyspin_encoding:
      raise ValueError(f"Unsupported pixel format {pixel_format}")
      
    return pyspin_encoding[pixel_format]


  def release(self):
    self._image.Release()
    del self._image
