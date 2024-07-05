
from typing import List
from harvesters.core import Harvester, ImageAcquirer


class Camera:
  def __init__(self, image_acquirer:ImageAcquirer):
    self.ia = image_acquirer

    self._setup_buffers()


  def _setup_buffers(self, num_buffers, num_buffers_to_hold):
    self.ia.num_buffers = num_buffers
    self.ia.num_filled_buffers_to_hold = num_buffers_to_hold


  # def start_camera(self):
    






class Manager:
    def __init__(self, cti_file:str):
    
      # Initialize Harvester
      self.h = Harvester()
      self.h.add_file(cti_file, check_validity=True, check_existence=True)  
      self.h.update()


    def camera_serials(self) -> List[str]:
      devices = self.h.device_info_list
      return [device.property_dict['serial_number'] for device in devices]


    def init_camera(self, serial:str) -> Camera:
      ia = self.h.create({'serial_number': str(serial)})
      return Camera(ia)