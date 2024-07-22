from collections import deque
import logging
from typing import Optional, Set
from beartype.typing import Callable, Dict

from beartype import beartype

from camera_driver.data.util import lerp
from camera_driver.driver.interface import Buffer
from camera_driver.data import Timestamped
from camera_driver.concurrent.work_queue import WorkQueue
from pydispatch import Dispatcher

from .frame_grouper import FrameGrouper

TimeQuery = Callable[[], float]
ProcessBuffer = Callable[[Buffer], Timestamped]


class SyncHandler(Dispatcher):
  _events_ = ["on_group"]

  @beartype
  def __init__(self, camera_set:Set[str], 
          sync_threshold:float, 
          sync_timeout:float, 

          process_buffer:ProcessBuffer,
          query_time:TimeQuery,  

          time_offsets:Optional[Dict[str, float]],
          logger:logging.Logger):
    
    
    self.sync_threshold = sync_threshold
    self.sync_timeout = sync_timeout
    self.logger = logger

    self.process_buffer = process_buffer

    self.camera_set = camera_set

    self.grouper = FrameGrouper(time_offsets, sync_timeout, sync_threshold)
    self.work_queue = WorkQueue("sync_handler", self._process_worker, 
                                logger=logger, num_workers=1, max_size=self.num_cameras)
    
    self.query_time = query_time
    self.clock_drift = 0.0

    self.most_recent_frame = 0.0
    
  @property
  def num_cameras(self):
    return self.camera_set.num_cameras
  

  def push_image(self, buffer:Buffer):
    if not self.work_queue.started:
      self.work_queue.start()
    self.work_queue.enqueue(buffer)


  def _process_worker(self, buffer:Buffer):
    image = self.process_buffer(buffer)
    group = self.grouper.add_frame(image)

    if group is not None:
      self.grouper.update_offsets(group)      

      t = group.timestamp
      frames = {k:frame.with_timestamp(t) for k,frame in group.frames.items()}

      self.clock_drift = lerp(0.02, group.clock_time - t, self.clock_drift)
      self.most_recent_frame = t
      
      self.emit("on_group", frames)

    timed_out = self.grouper.timeout_groups(self.query_time() - self.sync_timeout)
    for group in timed_out:
      missing = self.camera_set - group.camera_set
      self.logger.warning(f"Dropping timed out, missing {missing}")

    buffer.release()


  def flush(self):
    self.work_queue.stop()
    self.grouper.clear()

