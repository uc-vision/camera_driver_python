
from logging import Logger
import logging
from threading import Thread
from typing import Dict, List
from beartype import beartype
from beartype.typing import  Callable, Optional, Tuple
from camera_driver.data.util import dict_item
from ids_peak import ids_peak


from camera_driver.driver import interface
from camera_driver.data.encoding import ImageEncoding, camera_encodings

from .buffer import Buffer
from . import helpers



class Camera(interface.Camera):

  def __init__(self, name:str, device:ids_peak.Device, presets:interface.Presets, logger:Logger):
    self.device = device

    self.nodemap = device.RemoteDevice().NodeMaps()[0]
    self.data_stream = device.DataStreams()[0].OpenDataStream()

    self.stream_nodemap = self.data_stream.NodeMaps()[0]
    self.logger = logger


    self.capture_thread:Optional[Thread] = None
    self.started = False

    self.name = name
    self.presets = presets


  def compute_clock_offset(self, get_time_sec:Callable[[], float]):
    raise NotImplementedError()
  
  @beartype
  def setup_mode(self, mode:str="slave"):
    self.log(logging.INFO, f"Loading camera configuration ({mode})...")
    
    helpers.set_value(self.nodemap, "UserSetSelector", "Default")
    helpers.execute_wait(self.nodemap, "UserSetLoad")

    self._set_settings(self.stream_nodemap, self.presets['stream'])
    self._set_settings(self.nodemap, self.presets['device'])
    self._set_settings(self.nodemap, self.presets[mode])

  
  def _set_settings(self, nodemap, config:Dict[str, Dict]):
    for setting in config:
        setting_name, value = dict_item(setting)
        self.log(logging.DEBUG, f"Setting {setting_name} to {value}")

        try:
          helpers.set_value(nodemap, setting_name, value)
        except helpers.NodeException as e:
          self.log(logging.WARNING, f"Failed to set {setting_name} to {value}: {e}")

  def update_properties(self, settings: interface.CameraProperties):
    if helpers.is_writable(self.nodemap, "AcquisitionFrameRate"):
      helpers.set_value(self.nodemap, "AcquisitionFrameRate", settings.framerate)

    helpers.set_value(self.nodemap, "Gain", max(1.0, settings.gain))
    helpers.set_value(self.nodemap, "ExposureTime", int(settings.exposure))

  def camera_info(self) -> interface.CameraInfo:
    return interface.CameraInfo(
      name=self.name,
      serial=self.serial,
      image_size=self.image_size,
      encoding=self.encoding,
      model=self.model,
      throughput_mb=self.throughput_mb,
      has_latching=False
    )

  @property
  def model(self) -> str:
    return self.node_value("DeviceModelName")


  @property
  def throughput_mb(self) -> Tuple[float, float]:
    t = self.node_value("DeviceLinkCurrentThroughput")
    t_max = self.node_value("DeviceLinkThroughputLimit")

    return (t / 1e6, t_max / 1e6)
  

  def node_value(self, name:str):
    return helpers.node_value(self.nodemap, name)


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
    buffer_count = self.data_stream.NumBuffersAnnouncedMinRequired()

    self.log(logging.DEBUG, f"Allocating {buffer_count} buffers of size {payload_size/1e6:.1f}MB")

    for _ in range(buffer_count):
      buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
      self.data_stream.QueueBuffer(buffer)

  def _flush_buffers(self):
    self.log(logging.DEBUG, "Flushing buffers...")

    self.data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)
    for buffer in self.data_stream.AnnouncedBuffers():
        self.data_stream.RevokeBuffer(buffer)
  



  def _capture_thread(self):
    while self.started:
      try:
        raw_buffer = self.data_stream.WaitForFinishedBuffer(ids_peak.DataStream.INFINITE_NUMBER)  
      except ids_peak.AbortedException:
        break

      if raw_buffer.IsIncomplete():
        self.log(logging.WARNING, "Recieved incomplete buffer")
        continue  
            
      buffer = Buffer(self.name, raw_buffer)
      self.emit("on_buffer", buffer)

  def log(self, level:int, message:str):
    self.logger.log(level, f"{self.name}:{message}")

    
  def start(self):
    self.log(logging.INFO, "Starting camera capture...")
    self._setup_buffers()

    self.capture_thread = Thread(target=self._capture_thread)

    self.nodemap.FindNode("TLParamsLocked").SetValue(1)
    self.data_stream.StartAcquisition()
    helpers.execute_wait(self.nodemap, "AcquisitionStart")

    self.started = True
    self.log(logging.INFO, "started.")

    self.emit("on_started", True)
    self.capture_thread.start()

  def stop(self):
    self.logger.info(f"{self.name}:Stopping camera capture...")

    self.data_stream.StopAcquisition()
    helpers.execute_wait(self.nodemap, "AcquisitionStop")
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