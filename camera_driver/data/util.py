from queue import Empty, Queue
import threading
from typing import Any, Dict, List


def transpose_dicts_list(dicts:List[Dict[str, Any]]) -> Dict[str, List[Any]]:

  keys = dicts[0].keys()
  return {key:[d[key] for d in dicts] for key in keys}


def wait_for(dispatcher, name, timeout=10):

  queue = Queue()  
  def f(result):
    queue.put(result)

  dispatcher.bind(**{name:f})

  try:
    result = queue.get(timeout=timeout)
  except Empty as e:
    result = None

  dispatcher.unbind(f)
  return result