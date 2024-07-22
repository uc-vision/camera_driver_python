
from logging import Logger
from beartype.typing import Dict, List, Tuple
from camera_driver.driver.interface import CameraInfo
import torch

from pydispatch import Dispatcher
from beartype import beartype

from camera_driver.concurrent.taichi_queue import TaichiQueue
from camera_driver.concurrent.work_queue import WorkQueue
from camera_driver.pipeline.config import ImageSettings, ToneMapper, Transform
from camera_driver.data import BayerPattern, bayer_pattern, encoding_bits

from .image_outputs import ImageOutputs
from .camera_image import CameraImage

from taichi_image import camera_isp, interpolate, bayer, packed


class FrameProcessor(Dispatcher):
  """ FrameProcessor - process raw 12/16 bit images from cameras into tonemapped RGB images
  """
  _events_ = ["on_frame"]

  @beartype
  def __init__(self, cameras:Dict[str, CameraInfo], settings:ImageSettings, logger:Logger, device:torch.device, num_workers:int=4, max_size:int=4):
    self.settings = settings
    self.cameras = cameras
    self.logger = logger
    self.device = device

    self.queue = WorkQueue("frame_processor", run=self.process_worker, 
                           logger=logger, num_workers=num_workers, max_size=max_size)

    self.processor = TaichiQueue.run_sync(self._init_processor, cameras)
    self.queue.start()

    self.warmup()


  def update_settings(self, settings:ImageSettings):
    self.settings = settings
    transform = interpolate.ImageTransform(Transform(settings.transform).name)
    
    self.isp.set(moving_alpha=self.settings.moving_average, 
                 resize_width=int(self.settings.resize_width),
                 transform=transform)


  @beartype
  def _init_processor(self, cameras:Dict[str, CameraInfo]):
    enc = common_value("encoding", [camera.encoding for camera in cameras.values()])    
    
    self.pattern = bayer_pattern(enc)
    self.bits = encoding_bits(enc)

    if encoding_bits(enc) not in [12, 16]:
      raise ValueError(f"Unsupported bits {encoding_bits(enc)} in {enc}")


    transform = interpolate.ImageTransform(Transform(self.settings.transform).name)
    self.isp = camera_isp.Camera16(taichi_pattern[self.pattern], 
                         resize_width=int(self.settings.resize_width), 
                         moving_alpha=self.settings.moving_average,
                         transform=transform,
                         device=self.device)
    
  
  def warmup(self):
    """ Warm start - run some empty images through to avoid delay at later stage """
    def f():
      test_images = [empty_test_image(camera.image_size, device=self.device) 
                     for camera in self.cameras.values()]
      
      self._process_images(test_images)

    self.logger.info("FrameProcessor warmup")
    TaichiQueue.run_sync(f)



  @beartype
  def process_image_set(self, images:Dict[str, CameraImage]):
    assert set(images.keys()) == set(self.cameras.keys()
      ), f"Expected {set(self.cameras.keys())} - got {set(images.keys())}"
    
    return self.queue.enqueue(images)


  def _check_image(self, k:str, image:torch.Tensor):
    assert image.dtype == torch.uint8, f"{k}: expected uint8 buffer - got {image.dtype}"

    w, h = self.cameras[k].image_size
    return image.view(h, -1).to(self.device, non_blocking=True)

  

  @beartype
  def process_worker(self, camera_images:Dict[str, CameraImage]):
    images = [self._check_image(k, image.image_data) 
              for k, image in camera_images.items()]

    images = TaichiQueue.run_sync(self._process_images, images)
    outputs = {k:ImageOutputs(
      raw = camera_images[k], 
      rgb = image, 
      calibration=self.cameras[k].calibration,
      settings = self.settings)
                    for k, image in zip(camera_images.keys(), images)}

    self.emit("on_frame", outputs)

  @beartype
  def _process_images(self, images:List[torch.Tensor]):
    load_data = self.isp.load_packed12 if self.bits == 12 else self.isp.load_packed16
    images =  [load_data(image) for image in images]

    settings = self.settings

    if settings.tone_mapping == ToneMapper.linear:
      outputs = self.isp.tonemap_linear(images, gamma=settings.tone_gamma)
    elif settings.tone_mapping == ToneMapper.reinhard:
      outputs = self.isp.tonemap_reinhard(
        images, gamma=settings.tone_gamma, 
        intensity = settings.tone_intensity,
        light_adapt = settings.light_adapt,
        color_adapt = settings.color_adapt)
      
    return outputs


  def stop(self):
    self.queue.stop()


def empty_test_image(image_size:Tuple[int, int], pattern = bayer.BayerPattern.RGGB, device="cpu"):
  w, h = image_size
  test_image = torch.rand( (h, w, 3), dtype=torch.float32, device=device)
  
  cfa = bayer.rgb_to_bayer(test_image, pattern=pattern) 
  return packed.encode12(cfa, scaled=True) 



def common_value(name, values):
  assert len(set(values)) == 1, f"All cameras must have the same {name}"
  return values[0]

taichi_pattern = {
    BayerPattern.BGGR: bayer.BayerPattern.BGGR,
    BayerPattern.RGGB: bayer.BayerPattern.RGGB,
    BayerPattern.GBRG: bayer.BayerPattern.GBRG,
    BayerPattern.GRBG: bayer.BayerPattern.GRBG,
}