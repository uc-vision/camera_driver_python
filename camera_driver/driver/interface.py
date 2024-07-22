
from enum import Enum
from typing import List, Optional
from beartype.typing import Callable, Set, Tuple, Dict
import abc
import importlib
import logging

from beartype import beartype
import numpy as np

from pydispatch import Dispatcher
from camera_driver.data.encoding import ImageEncoding


from dataclasses import dataclass
from camera_geometry import Camera

@beartype
@dataclass
class CameraProperties:
  
  exposure: int
  gain: float
  framerate: float

SettingList = List[Dict]
Presets = Dict[str, SettingList]

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

  


@beartype
@dataclass
class CameraInfo:
  name : str
  serial:str
  
  image_size:Tuple[int, int]
  encoding : ImageEncoding

  throughput_mb : Tuple[float, float] 
  model : str 

  calibration : Optional[Camera] = None
  has_latching : bool = False

  def __repr__(self):    
    w, h = self.image_size
    t, t_max = self.throughput_mb
    return f"CameraInfo({self.name}:{self.serial} {self.model} {w}x{h} {self.encoding} {t:.1f}/{t_max:.1f}MB/s)"


class Camera(Dispatcher, metaclass=abc.ABCMeta):
  _events_ = ["on_started", "on_buffer"]

  @abc.abstractmethod
  def setup_mode(self, mode:str):
    raise NotImplementedError()
  
  @abc.abstractmethod
  def compute_clock_offset(self, get_time_sec:Callable[[], float]):
    raise NotImplementedError()
  
  @abc.abstractmethod
  def camera_info(self) -> CameraInfo:
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


  ids_peak = "ids_peak"
  spinnaker = "spinnaker"

  def create(self, presets:Dict[SettingList], logger:logging.Logger) -> Manager:
    match self:
      case BackendType.ids_peak:

        if importlib.util.find_spec("ids_peak") is None:
          raise ImportError("Please install the IDS Peak SDK and ids_peak python package.")

        from camera_driver.driver import peak
        return peak.Manager(presets, logger)

      case BackendType.spinnaker:
        if importlib.util.find_spec("PySpin") is None:      
          raise ImportError("Please install the Spinnaker SDK and PySpin python package.")

        from camera_driver.driver import spinnaker
        return spinnaker.Manager(presets, logger)
