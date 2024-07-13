from __future__ import annotations
from logging import Logger
import traceback
from typing import Callable, Any, List, Optional

from queue import Queue
from threading import Thread


class WorkQueue():
  def __init__(self, name: str, run: Callable, logger: Logger, 
               num_workers: int = 1, max_size: int = None):
    
    self.queue: Queue = Queue(max_size or num_workers)
    self.workers: Optional[List[Thread]] = None
    self.num_workers: int = num_workers
    
    self.name: str = name
    self.run: Callable = run
    self.logger: Logger = logger
    
  def enqueue(self, data: Any) -> None:
      assert self.started, f"WorkQueue {self.name} not started"
      return self.queue.put(data)
  
  def run_worker(self) -> None:
      try:
        data = self.queue.get()
        while data is not None:
          self.run(data)
          data = self.queue.get()
      except Exception as e:
        trace = traceback.format_exc()
        self.logger.error(trace)
        self.logger.error(f"Exception in {self.name}: {e}")
        
  @property
  def started(self) -> bool:
    return self.workers is not None
  
  @property
  def worker_ids(self) -> List[int]:
    return [worker.ident for worker in self.workers]
  
  def stop(self) -> None:
    self.logger.info(f"Stopping WorkQueue {self.name}, ({self.num_workers} threads)")
    
    for worker in self.workers:
      self.queue.put(None)
    
    for worker in self.workers:
      worker.join()
    self.logger.info(f"Workqueue done {self.name}")
  
  def start(self) -> None:
    assert self.workers is None
    self.workers = [Thread(target=self.run_worker) for _ in range(self.num_workers)]
    for worker in self.workers:
      worker.start()
  