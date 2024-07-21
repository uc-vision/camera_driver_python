import logging
from typing import Dict, List, Optional, Set
from beartype.typing import Callable

from beartype import beartype
from camera_driver.data.util import transpose_dicts_list
import numpy as np

from .frame_grouper import FrameGroup, FrameGrouper

from camera_driver.driver.interface import Buffer
from camera_driver.data import Timestamped
from pydispatch import Dispatcher


TimeQuery = Callable[[], float]
ProcessBuffer = Callable[[Buffer], Timestamped]


class Initialiser(Dispatcher):
  _events_ = ["initialized"]

  @beartype
  def __init__(self, 
          cameras : Set[str],
          query_time:TimeQuery,  

          init_window:int,
          sync_threshold:float,  

          logger:logging.Logger):
    
    self.timestamps:Dict[str, List[Timestamped]] = {camera:[] for camera in cameras}
    self.query_time = query_time
    self.logger = logger

    self.frame_window = init_window
    self.sync_threshold = sync_threshold
    

  def try_initialise(self) -> Optional[Dict[str, float]]:
    if not self.has_minimum_frames():
      return
      
    offsets = {k:np.median([offset.clock_time_sec - offset.timestamp_sec for offset in offsets])
                for k, offsets in self.timestamps}

    groups:List[FrameGroup] = []

    grouper = FrameGrouper(offsets, self.sync_threshold * 2)
    for _, camera_stamps in self.timestamps.items():
      for stamp in camera_stamps:
        group = grouper.add_frame(stamp)
        if group is not None:
          groups.append(group)


    mean_offsets = {k: offsets[k] + np.mean(offsets) for k, offsets in 
                    transpose_dicts_list(group.time_offsets).items()}

    return mean_offsets
    
      
  def frame_counts(self):
    return {k:len(v) for k,v in self.timestamps.items()}


  def has_minimum_frames(self):    
    for stamps in self.timestamps.values():
      if len(stamps) < self.frame_window:
        return False
      
    return True
    
  def push_image(self, buffer:Buffer): 
    now = self.query_time()

    stamps = self.timestamps[buffer.camera_name]
    stamps.append(
      Timestamped(buffer.timestamp_sec, now, buffer.camera_name))
    
    offsets = self.try_initialise() 
    if offsets is not None:
      self.emit("initialized", offsets)
      

  
