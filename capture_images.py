
from datetime import datetime
import logging
from time import sleep

import torch

from camera_driver.camera_interface import Buffer
from argparse import ArgumentParser

from camera_driver.config import load_yaml
from camera_driver.camera_set import CameraSet


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def main():

  parser = ArgumentParser()
  parser.add_argument("--config", type=str, required=True)
  parser.add_argument("--settings", type=str, required=True)
  args = parser.parse_args()


  config = load_yaml(args.config)
  camera_settings = load_yaml(args.settings)

  def get_timestamp():
    return datetime.now().timestamp()
  
  camera_set = CameraSet.from_config(logger, config, camera_settings)
  offsets = camera_set.compute_clock_offsets(get_timestamp)
  print(offsets)

  try:

    def on_buffer(buffer:Buffer):
      image = buffer.image(device=torch.device("cuda", 0))
      print(image)

      buffer.release()

    camera_set.bind(on_buffer=on_buffer)
    camera_set.start()

    sleep(5)

  finally:
    camera_set.release()


    
if __name__ == '__main__':
  main()