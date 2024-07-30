from dataclasses import replace
from datetime import datetime
from beartype.typing import Dict, List, Optional
import numpy as np

from camera_driver.data import Timestamped


def nearest_minute(timestamp:datetime):
  return datetime(timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, 0)




class FrameGroup:
  def __init__(self, frame:Timestamped):
    self.frames = {frame.camera_name:frame}
    
  def can_group(self, frame:Timestamped, threshold_sec:float=0.05):
    return (frame.camera_name not in self.frames 
            and abs(frame.timestamp_sec - self.timestamp) <= threshold_sec)


  def __repr__(self):
    times = ", ".join([f"{name}: {frame.datetime.strftime('%S.%f')}" for name, frame in self.frames.items()])
    return f"FrameGroup({times})"

  @property
  def date(self):
    return datetime.fromtimestamp(self.timestamp)

  @property
  def timestamp(self):
    return np.mean([frame.timestamp_sec for frame in self.frames.values()]) 
  
  @property 
  def clock_time(self):
    return np.mean([frame.clock_time_sec for frame in self.frames.values()]) 


  
  @property
  def camera_set(self) -> set[str]:
    return set(sorted(self.frames.keys()))
  

  def __len__(self) -> int:
    return len(self.frames)
  
  def append(self, frame:Timestamped):
    assert frame.camera_name not in self.frames, f"frame from {frame.camera_name} already in group"
    self.frames[frame.camera_name] = frame

  @property
  def time_offsets(self):
    # compute time offset relative to mean timestamp
    return {name:frame.timestamp_sec - self.timestamp 
            for name, frame in sorted(self.frames.items())}
    

  @property
  def time_offset_vec(self):
    return np.array(list(self.time_offsets.values()))



class FrameGrouper():
  def __init__(self, time_offsets:Dict[str, float], threshold_sec:float=0.05):
    self.threshold_sec = threshold_sec

    self.time_offsets = time_offsets
    self.groups:List[FrameGroup] = []

    self.camera_set = set(self.time_offsets.keys())
    
  @property
  def num_cameras(self):
    return len(self.time_offsets)
  
  def clear(self):
    self.groups = []
    
  @property
  def time_offset_vec(self):
    return np.array(sorted(self.time_offsets).values())

  def group_frame(self, frame:Timestamped) -> FrameGroup:
    for group in self.groups:
      if group.can_group(frame, self.threshold_sec):
        group.append(frame)
        return group
      
    group = FrameGroup(frame)
    self.groups.append(group)
    return group   
  
  @property
  def sorted_groups(self):
    return sorted(self.groups, key=lambda group: group.timestamp)
      
  def update_offsets(self, group:FrameGroup):
    """
    Update time offsets based on differences from the mean timestamp.
    """
    for name, offset in group.time_offsets.items():
      self.time_offsets[name] -= offset

  def set_offsets(self, offsets:Dict[str, float]):
    assert set(offsets.keys()) == self.camera_set, "offsets must match camera set"
    self.time_offsets = offsets


  def timeout_groups(self, timeout_time:float) -> List[FrameGroup]:
    timed_out = [group for group in self.groups
                  if timeout_time > group.timestamp ]

    for group in timed_out:
      self.groups.remove(group)

    return timed_out

  def add_frame(self, frame:Timestamped) -> Optional[FrameGroup]:
    frame = replace(frame, timestamp_sec=frame.timestamp_sec + self.time_offsets[frame.camera_name])

    group = self.group_frame(frame)      
    if len(group) == self.num_cameras:
      self.groups.remove(group)      
      return group
    
    return None