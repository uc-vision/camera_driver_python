
from dataclasses import dataclass, replace
from datetime import datetime



@dataclass
class Timestamped:

  timestamp_sec: float
  camera_name: str

  @property
  def datetime(self):
    return datetime.fromtimestamp(self.timestamp_sec)
  
  @property
  def stamp_pretty(self):
    return self.datetime.strftime('%M%S.3f')

  def with_timestamp(self, timestamp_sec:float):
    return replace(self, timestamp_sec=timestamp_sec)

  