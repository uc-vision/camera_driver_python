
from logging import Logger
import logging
from threading import Thread
from typing import Dict, List
from beartype.typing import  Callable, Optional, Tuple
from ids_peak import ids_peak

from pydispatch import Dispatcher

from camera_driver.driver import interface
from camera_driver.data.encoding import ImageEncoding, camera_encodings
from .buffer import Buffer




class Camera(Dispatcher):
  _events_ = ["on_started", "on_buffer"]

  def __init__(self, name:str, device:ids_peak.Device, presets:Dict[interface.SettingList], logger:Logger):
    self.device = device

    self.nodemap = device.RemoteDevice().NodeMaps()[0]
    self.data_stream = device.DataStreams()[0].OpenDataStream()
    self.logger = logger


    self.capture_thread:Optional[Thread] = None
    self.started = False

    self.name = name
    self.presets = presets


  def compute_clock_offset(self, get_time_sec:Callable[[], float]):
    raise NotImplementedError()
  
  def setup_mode(self, mode:str):
    raise NotImplementedError()


  @property
  def image_size(self) -> Tuple[int, int]:
    w = self.node_value("Width")
    h = self.node_value("Height")
    return w, h

  
  @property
  def encoding(self) -> ImageEncoding:
    pixel_format = self.node_value("PixelFormat")
    return camera_encodings[pixel_format]
    
  @property
  def serial(self) -> str:
    return self.node_value("DeviceSerialNumber")  

  def __repr__(self):
    w, h = self.image_size
    return f"peak.Camera({self.name}:{self.serial} {w}x{h} {self.encoding})"



  def _setup_buffers(self):
    self.nodemap.FindNode("PayloadSize").Value()

    payload_size = self.nodemap.FindNode("PayloadSize").Value()
    buffer_count_max = self.data_stream.NumBuffersAnnouncedMinRequired()

    for _ in range(buffer_count_max):
      buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
      self.data_stream.QueueBuffer(buffer)

  def _flush_buffers(self):
    self.log(logging.DEBUG, "Flushing buffers...")

    self.data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
    for buffer in self.data_stream.AnnouncedBuffers():
        self.data_stream.RevokeBuffer(buffer)

  def execute_wait(self, node_name:str):
     node = self.nodemap.FindNode(node_name)
     node.Execute()
     node.WaitUntilDone()

  def node_value(self, node_name:str):
    node = self.nodemap.FindNode(node_name)
    
    if node.Type() == ids_peak.NodeType_Enumeration:
      return node.CurrentEntry().DisplayName()
    else:
      return node.Value()

  def _capture_thread(self):
    while self.started:
      raw_buffer = self.data_stream.WaitForFinishedBuffer(ids_peak.DataStream.INFINITE_NUMBER)  

      if raw_buffer.IsIncomplete():
        self.log(logging.WARNING, "Recieved incomplete buffer")
        continue  
            
      buffer = Buffer(self.name, raw_buffer)
      self.emit("on_buffer", buffer)

  def log(self, level:int, message:str):
    self.logger.log(level, f"{self.name}:{message}")

  def update_settings(self, settings:interface.CameraProperties):
    raise NotImplementedError() # TODO


    
  def start(self):
    self.log(logging.INFO, "Starting camera capture...")
    self._setup_buffers()

    self.capture_thread = Thread(target=self._capture_thread)

    self.nodemap.FindNode("TLParamsLocked").SetValue(1)
    self.data_stream.StartAcquisition()
    self.execute_wait("AcquisitionStart")

    self.started = True
    self.log(logging.INFO, "started.")

    self.emit("on_started", True)
    self.capture_thread.start()

  def stop(self):
    self.logger.info(f"{self.name}:Stopping camera capture...")

    self.data_stream.StopAcquisition()
    self.execute_wait("AcquisitionStop")
    self.nodemap.FindNode("TLParamsLocked").SetValue(0)

    self.started = False

    self.log(logging.DEBUG, f"Waiting for capture thread {self.capture_thread}...")
    self.data_stream.KillWait()

    self.capture_thread.join()
    self.capture_thread = None

    self._flush_buffers()

    self.log(logging.INFO, "stopped.")
    self.emit("on_started", False)


  def release(self):
    if self.started:
      self.stop()