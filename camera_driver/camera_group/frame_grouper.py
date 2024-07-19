from dataclasses import replace
from datetime import datetime
from beartype.typing import Dict, List, Optional
import numpy as np

from camera_driver.data import Timestamped


def nearest_minute(timestamp:datetime):
  return datetime(timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, 0)




class FrameGroup:
  def __init__(self, frame:Timestamped, expected_cameras:set[str]):
    self.frames = {frame.camera_name:frame}
    self.expected_cameras = expected_cameras
    
  def can_group(self, frame:Timestamped, threshold_sec:float=0.05):
    return (frame.camera_name not in self.frames 
            and abs(frame.timestamp_sec - self.timestamp) <= threshold_sec)


  def __repr__(self):
    times = ", ".join([f"{name}: {frame.datetime.strftime('%M%S.3f')}" for name, frame in self.frames.items()])
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
    return set(self.frames.keys())
  
  @property
  def missing_cameras(self) -> set[str]:
    return self.expected_cameras - self.camera_set

  def __len__(self) -> int:
    return len(self.frames)
  
  def append(self, frame:Timestamped):
    assert frame.camera_name not in self.frames, f"frame from {frame.camera_name} already in group"
    self.frames[frame.camera_name] = frame

  @property
  def time_offsets(self):
    # compute time offset relative to mean timestamp
    return {name:frame.timestamp_sec - self.timestamp for name, frame in self.frames.items()}



class FrameGrouper():
  def __init__(self, time_offsets:Dict[str, float], timeout_sec:float=2.0, threshold_sec:float=0.05):
    self.timeout_sec = timeout_sec
    self.threshold_sec = threshold_sec

    self.time_offsets = time_offsets
    self.groups:List[FrameGroup] = []

    self.camera_set = set(self.time_offsets.keys())
    
  @property
  def num_cameras(self):
    return len(self.time_offsets)
  
  def clear(self):
    self.groups = []
    

  def group_frame(self, frame:Timestamped) -> FrameGroup:
    for group in self.groups:
      if group.can_group(frame, self.threshold_sec):
        group.append(frame)
        return group
      
    group = FrameGroup(frame, self.camera_set)
    self.groups.append(group)
    return group   
      
  def update_offsets(self, group:FrameGroup):
    """
    Update time offsets based on differences from the mean timestamp.
    """
    for name, offset in group.time_offsets.items():
      self.time_offsets[name] -= offset


  def timeout_groups(self, current_time:float) -> List[FrameGroup]:
    timed_out = [group for group in self.groups
                  if current_time - group.timestamp > self.timeout_sec]

    for group in timed_out:
      self.groups.remove(group)

    return timed_out

  def add_frame(self, frame:Timestamped) -> Optional[FrameGroup]:
    frame = replace(frame, timestamp_sec=frame.timestamp_sec + self.time_offsets[frame.camera_name])

    group = self.group_frame(frame)      
    if len(group) == self.num_cameras:
      self.groups.remove(group)
      self.update_offsets(group)      
      
      return group
    return None