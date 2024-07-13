
from enum import Enum
from typing import Callable, Set, Tuple
import abc
import importlib
import logging

from beartype import beartype
import numpy as np

from pydispatch import Dispatcher
from .data.encoding import ImageEncoding


from dataclasses import dataclass

@beartype
@dataclass
class CameraProperties:
  
  exposure: int
  gain: float
  framerate: float

  
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
  def load_config(self, config:dict, mode:str="slave"):
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
    pass

  @abc.abstractmethod
  def reset_cameras(self, camera_set:Set[str]):
    pass

  @abc.abstractmethod
  def init_camera(self, camera_name:str, serial:str) -> Camera:
    pass

  @abc.abstractmethod
  def release(self):
    pass


class BackendType(Enum):
  peak = "peak"
  spinnaker = "spinnaker"


@beartype
def create_manager(backend:BackendType, logger:logging.Logger):
  if backend is BackendType.spinnaker:
    if importlib.util.find_spec("PySpin") is None:      
      raise ImportError("Please install the Spinnaker SDK and PySpin python package.")

    from camera_driver import spinnaker
    return spinnaker.Manager(logger)
  elif backend is BackendType.peak:

    if importlib.util.find_spec("ids_peak") is None:
      raise ImportError("Please install the IDS Peak SDK and ids_peak python package.")

    from camera_driver import peak
    return peak.Manager(logger)

  else:
    raise ValueError(f"Unknown backend: {backend}")

