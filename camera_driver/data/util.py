from queue import Empty, Queue
import threading
from typing import Any, Dict, List

from beartype import beartype

@beartype
def transpose_dicts_list(dicts:List[Dict[str, Any]]) -> Dict[str, List[Any]]:
  assert len(dicts) > 0, "transpose_dicts_list: empty list"

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


def lerp(t, a, b):
  return a + t * (b - a)



def dict_item(d:Dict):
  k = next(iter(d)) # setting.keys()[0]
  v = d[k]
  return k, v