
from enum import Enum
from typing import List
from beartype.typing import Callable, Set, Tuple, Dict
import abc
import importlib
import logging

from beartype import beartype
import numpy as np

from pydispatch import Dispatcher
from camera_driver.data.encoding import ImageEncoding


from dataclasses import dataclass

@beartype
@dataclass
class CameraProperties:
  
  exposure: int
  gain: float
  framerate: float

SettingList = List[Dict]


  
class Buffer(metaclass=abc.ABCMeta):

  @property
  @abc.abstractmethod
  def camera_name(self) -> str:
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def image_data(self) -> np.ndarray:
    """ Note this data is invalidated when the image is released, so must be copied."""
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def image_size(self) -> Tuple[int, int]:
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def timestamp_sec(self) -> float:
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def encoding(self) -> ImageEncoding:
    raise NotImplementedError()

  @abc.abstractmethod
  def release(self):
    raise NotImplementedError()

  

class Camera(Dispatcher, metaclass=abc.ABCMeta):
  _events_ = ["on_started", "on_buffer"]

  @abc.abstractmethod
  def setup_mode(self, mode:str):
    raise NotImplementedError()
  

  def compute_clock_offset(self, get_time_sec:Callable[[], float]):
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def image_size(self):
    raise NotImplementedError()


  @property
  @abc.abstractmethod
  def encoding(self) -> ImageEncoding:
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def serial(self) -> str:
    raise NotImplementedError()

  @property
  @abc.abstractmethod
  def model(self) -> str:
    raise NotImplementedError()
  
  @property
  @abc.abstractmethod
  def throughput_mb(self) -> Tuple[float, float]:
    raise NotImplementedError()
  



  @abc.abstractmethod
  def update_properties(self, settings:CameraProperties):
    raise NotImplementedError()

  @abc.abstractmethod
  def stop(self):
    raise NotImplementedError()

  @abc.abstractmethod
  def release(self):
    raise NotImplementedError()


  

class Manager(metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def camera_serials(self) -> Set[str]:
    raise NotImplementedError()

  @abc.abstractmethod
  def reset_cameras(self, camera_set:Set[str]):
    raise NotImplementedError()

  @abc.abstractmethod
  def wait_for_cameras(self, camera_set:Set[str]) -> Dict[str, Camera]:
    raise NotImplementedError()

  @abc.abstractmethod
  def init_camera(self, camera_name:str, serial:str) -> Camera:
    raise NotImplementedError()

  @abc.abstractmethod
  def release(self):
    raise NotImplementedError()


class BackendType(Enum):


  peak = "peak"
  spinnaker = "spinnaker"

  def create(self, presets:Dict[SettingList], logger:logging.Logger) -> Manager:
    match self:
      case BackendType.peak:

        if importlib.util.find_spec("ids_peak") is None:
          raise ImportError("Please install the IDS Peak SDK and ids_peak python package.")

        from camera_driver.driver import peak
        return peak.Manager(presets, logger)

      case BackendType.spinnaker:
        if importlib.util.find_spec("PySpin") is None:      
          raise ImportError("Please install the Spinnaker SDK and PySpin python package.")

        from camera_driver.driver import spinnaker
        return spinnaker.Manager(presets, logger)
