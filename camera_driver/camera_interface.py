from typing import Callable, Set
import abc
import importlib
import logging

import torch

from pydispatch import Dispatcher
from camera_driver.image.camera_image import CameraImage
from camera_driver.image.encoding import ImageEncoding


class Buffer(metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def image(self, device:torch.device) -> CameraImage:
    pass

  @abc.abstractmethod
  def release(self):
    pass
  

class Camera(Dispatcher, metaclass=abc.ABCMeta):
  _events_ = ["on_started", "on_buffer"]

  @abc.abstractmethod
  def load_config(self, config:dict, mode:str="slave"):
    pass

  @abc.abstractmethod
  def start(self):
    pass

  @abc.abstractmethod
  def stop(self):
    pass


  @abc.abstractmethod
  def release(self):
    pass


  def compute_clock_offset(self, get_time_sec:Callable[[], float]):
    pass

  @property
  @abc.abstractmethod
  def image_size(self):
    pass

  @property
  @abc.abstractmethod
  def encoding(self) -> ImageEncoding:
    pass
  
  @property
  @abc.abstractmethod
  def serial(self) -> str:
    pass


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



def create_manager(backend:str, logger:logging.Logger):
  if backend == "spinnaker":
    if importlib.util.find_spec("ids_peak") is None:      
      raise ImportError("Failed to import PySpin. Please install the Spinnaker SDK.")

    from camera_driver import spinnaker
    return spinnaker.Manager(logger)
  elif backend == "peak":

    if importlib.util.find_spec("ids_peak") is None:
      raise ImportError("Failed to import ids_peak. Please install the IDS Peak SDK.")

    from camera_driver import peak
    return peak.Manager(logger)

  else:
    raise ValueError(f"Unknown backend: {backend}")

