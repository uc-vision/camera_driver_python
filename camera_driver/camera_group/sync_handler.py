import logging
from typing import Set
from beartype.typing import Callable, Dict

from beartype import beartype

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
  def __init__(self, time_offsets:Dict[str, float], 
          sync_threshold:float, 
          sync_timeout:float, 

          process_buffer:ProcessBuffer,
          query_time:TimeQuery,  

          logger:logging.Logger):
    
    
    self.sync_threshold = sync_threshold
    self.sync_timeout = sync_timeout
    self.logger = logger

    self.process_buffer = process_buffer

    self.grouper = FrameGrouper(time_offsets, sync_timeout, sync_threshold)
    self.work_queue = WorkQueue("sync_handler", self._process_worker, 
                                logger=logger, num_workers=1, max_size=self.num_cameras)
    
    self.query_time = query_time
    

  @property
  def num_cameras(self):
    return self.grouper.num_cameras
  

  def push_image(self, buffer:Buffer):
    if not self.work_queue.started:
      self.work_queue.start()
    self.work_queue.enqueue(buffer)


  def _process_worker(self, buffer:Buffer):
    image = self.process_buffer(buffer)
    group = self.grouper.add_frame(image)

    if group is not None:
      t = group.timestamp
      frames = {k:frame.with_timestamp(t) for k,frame in group.frames.items()}

      self.emit("on_group", frames)

    timed_out = self.grouper.timeout_groups(self.query_time())
    for group in timed_out:
      self.logger.warning(f"Dropping timed out, missing {group.missing_cameras}")

    buffer.release()


  def flush(self):
    self.work_queue.stop()
    self.grouper.clear()

