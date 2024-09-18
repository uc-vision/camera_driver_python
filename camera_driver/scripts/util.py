

from collections import deque
from datetime import datetime
import logging
import math
from pathlib import Path
from queue import Queue
from typing import List, Optional
from beartype.typing import Dict, Tuple
from camera_driver.pipeline.pipeline import CameraPipeline
import numpy as np
import cv2

from camera_driver.concurrent import WorkQueue
from camera_driver.pipeline import CameraInfo, ImageOutputs


class ImageWriter():
  def __init__(self, scan_folder:str, num_cameras:int, logger:logging.Logger):

    self._scan_folder = Path(scan_folder)
    self._counter = 0

    self.encode_queue = WorkQueue("image_encoder", self._encode_image, logger=logger, 
                                num_workers=1, max_size=num_cameras)

    self.write_queue = WorkQueue("image_writer", self._process_image, logger=logger, 
                                num_workers=num_cameras, max_size=num_cameras * 4)

    self._is_started = False

    self.logger = logger

  def write_images(self, images:Dict[str, ImageOutputs]):
    for name, image in images.items():
      filename = self.scan_folder  / image.camera_name / f"image_{self.counter:04d}.jpg"
      self.encode_queue.enqueue((image, filename))

    self.counter = self.counter + 1

  def _encode_image(self, image_counter:Tuple[ImageOutputs, int]):
    image, filename = image_counter

    if self.write_queue.free == 0:
      self.warn(f"Write queue is full ({self.write_queue.size})")

    self.write_queue.enqueue((image.compressed, filename))


  def _process_image(self, image_counter:Tuple[ImageOutputs, int]):
    compressed, filename = image_counter
    filename.parent.mkdir(parents=True, exist_ok=True)

    with open(filename, "wb") as f:
      f.write(compressed)

  def stop(self):
    self.encode_queue.stop()
    self.write_queue.stop()
    self.is_started = False

  def start(self):
    self.write_queue.start()
    self.encode_queue.start() 
    self.is_started = True

  @property
  def is_started(self):
    return self._is_started

  @is_started.setter
  def is_started(self, value: bool):
    self._is_started = value

  @property
  def scan_folder(self):
    return self._scan_folder

  @scan_folder.setter
  def scan_folder(self, value: str):
    self._scan_folder = Path(value)

  @property
  def counter(self):
    return self._counter
  
  @counter.setter
  def counter(self, value: int):
    self._counter = value

  # -------------------------------------------
  #   Helpers
  # -------------------------------------------

  def info(self, msg):
    self.logger.info(msg)

  def error(self, msg):
    self.logger.error(msg)

  def warn(self, msg):
    self.logger.warning(msg)


class ImageGrid():

  def __init__(self, camera_sizes:List[Tuple[int, int]]):
    
    self.rows = math.ceil(math.sqrt(len(camera_sizes)))
    self.cols = math.ceil(len(camera_sizes) / self.rows)

    self.cell_size = (max([w for w, h in camera_sizes]), max([h for w, h in camera_sizes]))
    self.image = np.zeros((self.cell_size[1] * self.rows, self.cell_size[0] * self.cols, 3), dtype=np.uint8)
  
  def update(self, idx:int, image:np.ndarray):
    h, w = image.shape[:2]

    x = (idx % self.cols) * self.cell_size[0]
    y = (idx // self.cols) * self.cell_size[1]

    self.image[y:y+h, x:x+w, :] = image
  
  def image_size(self):
    return self.image.shape[1], self.image.shape[0]
  


def view_images(queue:Queue, camera_info:Dict[str, CameraInfo], preview_width):

  def resized(image_size):
    return (preview_width, int(preview_width * image_size[0] / image_size[1]))

  image_sizes = [resized(info.image_size) for info in camera_info.values()]
  camera_indexes = {k:i for i, k in enumerate(camera_info.keys())}

  grid = ImageGrid(image_sizes)

  cv2.namedWindow("images", cv2.WINDOW_NORMAL)
  cv2.resizeWindow("images", *grid.image_size())
  n = 0


  while True:
    image_group:Dict[str, ImageOutputs] = queue.get()
    n = n + len(image_group)

    for (k, image) in image_group.items():
      preview = image.preview.cpu().numpy()
      grid.update(camera_indexes[k], cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))
    
    if n > len(camera_info):
      cv2.imshow("image", grid.image)
      cv2.waitKey(1)
      n = n - len(camera_info)



class RateMonitor():
  def __init__(self, pipeline:CameraPipeline, logger:Optional[logging.Logger]=None, interval:float=2.0):
    self.pipeline = pipeline

    self.recieved = {k:deque(maxlen=20) for k in pipeline.camera_info.keys()}
    self.last_time = datetime.now().timestamp()

    self.pipeline.bind(on_image_set=self.on_group)
    self.interval = interval
    self.logger = logger

  def get_rates(self):
    def f(times):
      return 0.0 if len(times) < 2 else (len(times) - 1) / (times[-1] - times[0])
    return {k:f(times) for k, times in self.recieved.items()}
    

  def on_group(self, group:Dict[str, ImageOutputs]):
    for k, image in group.items():
      self.recieved[k].append(image.timestamp_sec)

    now = datetime.now().timestamp()
    if self.logger is not None and  now - self.last_time > self.interval:
      self.logger.info(self.format_rates())
      self.last_time = now


  def format_rates(self):
    formatted = [f"{k}:{rate:.2f}" for k, rate in self.get_rates().items()]
    return  ", ".join(formatted)
    

class Counter():
  def __init__(self, pipeline:CameraPipeline):
    self.pipeline = pipeline
    self.recieved = {k:int for k in pipeline.camera_info.keys()}

  def __enter__(self):
    self.recieved = {k:0 for k in self.pipeline.camera_info.keys()}
    self.pipeline.bind(on_image_set=self.on_group)

    return self
    
  def __exit__(self, exc_type, exc_value, traceback):
    self.pipeline.unbind(self.on_group)

  def on_group(self, group:Dict[str, ImageOutputs]):
    for k, image in group.items():
      self.recieved[k] += 1

