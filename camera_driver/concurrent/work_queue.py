from __future__ import annotations
from logging import Logger
import traceback
from typing import Callable

from queue import Queue
from threading import Thread


class WorkQueue():

  def __init__(self, name, run:Callable, logger:Logger, num_workers=1, max_size=None):
        
    self.queue = Queue(max_size or num_workers)
    self.workers = None
    self.num_workers = num_workers
    
    self.name = name
    self.run = run

    self.logger = logger

    
  def enqueue(self, data):
      assert self.started, f"WorkQueue {self.name} not started"
      return self.queue.put( data )
  
  def run_worker(self):
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
  def started(self):
    return self.workers is not None

  def stop(self):
    self.logger.loginfo(f"Waiting for {self.name}: threads {self.workers}")
    
    for worker in self.workers:
      self.queue.put(None)
    
    for worker in self.workers:
      worker.join()
    self.logger.loginfo(f"Done {self.name}: thread {self.workers}")


  def start(self):
    assert self.workers is None

    self.workers = [Thread(target = self.run_worker) 
                    for _ in range(self.num_workers)]
    for worker in self.workers:
      worker.start()