
import logging
from time import sleep

import torch
import yaml

from camera_driver.interface import Buffer, create_manager
from argparse import ArgumentParser


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def load_yaml(file):
  with open(file) as f:
    return yaml.load(f, Loader=yaml.Loader)
  





def main():

  parser = ArgumentParser()
  parser.add_argument("--config", type=str, required=True)
  parser.add_argument("--settings", type=str, required=True)
  args = parser.parse_args()



  camera_settings = load_yaml(args.settings)
  config = load_yaml(args.config)


  # serials:Dict[str, str] = config_file["cameras"]

  manager = create_manager(camera_settings["backend"], logger)

  logging.info(f"Found cameras {manager.camera_serials()}")
  
  if config["reset_cycle"] is True:
    manager.reset_cameras(manager.camera_serials())

  serial = manager.camera_serials().pop()
  camera = manager.init_camera("camera", serial)


  try:
    camera.load_config(camera_settings["camera_settings"], "master")

    def on_image(buffer:Buffer):
      image = buffer.image(device=torch.device("cuda", 0))
      print(image)

      buffer.release()


    camera.bind(on_image=on_image)
    camera.start()

    sleep(5)

  finally:
    camera.release()


    del camera
    manager.release()



if __name__ == '__main__':
  main()