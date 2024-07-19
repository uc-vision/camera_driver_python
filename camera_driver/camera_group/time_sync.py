import logging
from typing import Set
from beartype.typing import Callable, Dict

from beartype import beartype
import numpy as np

from camera_driver.driver.interface import Buffer
from camera_driver.data import Timestamped
from pydispatch import Dispatcher


TimeQuery = Callable[[], float]
ProcessBuffer = Callable[[Buffer], Timestamped]


class TimeSyncer(Dispatcher):
  _events_ = ["on_group"]

  @beartype
  def __init__(self, 
               start_time:float,
          cameras : Set[str],
          query_time:TimeQuery,  

          logger:logging.Logger):
    
    self.camera_offsets = {camera:[] for camera in cameras}
    self.query_time = query_time
    self.logger = logger
    self.start_time = start_time



  def push_image(self, buffer:Buffer):
    now = self.query_time()

    offsets = self.camera_offsets[buffer.camera_name]
    offsets.append(now - buffer.timestamp_sec)

    offsets = np.array(offsets[-10:])
    median = np.median(offsets)

    # self.logger.warn(f"{len(offsets)}: {buffer.camera_name} std = {np.std(offsets):.4f}")

    if len(offsets) == 10:
      self.logger.info(f"{buffer.camera_name} offset {median - self.start_time:.4f}")



