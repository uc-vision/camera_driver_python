from dataclasses import replace
from typing import Dict, List, Optional

from camera_driver.image.camera_image import CameraImage


class FrameGroup:
  def __init__(self, frame:CameraImage, expected_cameras:set[str]):
    self.frames = {frame.camera_name:frame}
    self.expected_cameras = expected_cameras
    
  def can_group(self, frame:CameraImage, threshold_sec:float=0.05):
    return (frame.camera_name not in self.frames 
            and abs(frame.timestamp_sec - self.timestamp) <= threshold_sec)

  @property
  def timestamp(self):
    return sum([frame.timestamp_sec for frame in self.frames.values()]) / len(self.frames)
  
  @property
  def camera_set(self) -> set[str]:
    return set(self.frames.keys())
  
  @property
  def missing_cameras(self) -> set[str]:
    return self.expected_cameras - self.camera_set

  def __len__(self) -> int:
    return len(self.frames)
  
  def append(self, frame:CameraImage):
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
      

  def group_frame(self, frame:CameraImage) -> FrameGroup:
    for group in self.groups:
      if group.can_group(frame, self.threshold_sec):
        group.append(frame)
        return group
      
    group = FrameGroup(frame)
    self.groups.append(group)
    return group   
      
  def update_offsets(self, group:FrameGroup):
    for name, offset in group.time_offsets.items():
      self.time_offsets[name] += offset


  def timeout_groups(self, current_time:float) -> List[FrameGroup]:
    timed_out = [current_time - group.timestamp > self.timeout_sec for group in self.groups]

    for group in timed_out:
      self.groups.remove(group)

    return timed_out

  def add_frame(self, frame:CameraImage):
    frame = replace(frame, timestamp_sec=frame.timestamp_sec + self.time_offsets[frame.camera_name])

    group = self.group_frame(frame)      
    if len(group) == self.num_cameras:
      self.groups.remove(group)

      self.update_offsets(group)

      mean_time = sum([frame.timestamp_sec for frame in group]) / self.num_cameras
      group = [replace(frame, timestamp_sec=mean_time) for frame in group]
      
    return group