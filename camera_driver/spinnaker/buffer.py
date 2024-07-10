import warnings

import numpy as np
import torch

from camera_driver.image import CameraImage
import PySpin

from camera_driver.image.camera_image import numpy_image
from camera_driver import camera_interface
from camera_driver.image.encoding import ImageEncoding


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



class Buffer(camera_interface.Buffer):
  def __init__(self, camera_name:str, image:PySpin.Image):
    assert not image.IsIncomplete()

    self.camera_name = camera_name
    self._image = image

  def image(self, device:torch.device) -> CameraImage:
    image_data = self._image.GetData().view(np.uint8)

    pixel_format = self._image.GetPixelFormat()
    if pixel_format not in pyspin_encoding:
      raise ValueError(f"Unsupported pixel format {pixel_format}")
      
    return CameraImage(
      self.camera_name,
      image_data = numpy_image(image_data, device=device),

      timestamp_sec=float(self._image.GetTimeStamp()) / 1e9,
      offset_sec = 0.,
      
      image_size = (self._image.GetWidth(), self._image.GetHeight()),
      encoding = pyspin_encoding[pixel_format]
    )

  def release(self):
    self._image.Release()
    del self._image
