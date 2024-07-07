
import logging
from time import sleep

import torch
import yaml
from camera_driver.spinnaker import Manager
from camera_driver.spinnaker.buffer import Buffer
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')


def main():

  manager = Manager(logger)
  print(manager.camera_serials())
  # manager.reset_cameras()


  config_file = "camera_12p.yaml"
  with open(config_file) as config_file:
     config = yaml.load(config_file, Loader=yaml.Loader)

  serial = manager.camera_serials()[0]
  camera = manager.init_camera("camera", serial)

  camera.load_config(config["camera_settings"])

  def on_image(buffer:Buffer):

    image = buffer.image(device=torch.device("cuda", 0))
    print(image)

    buffer.release()


  camera.bind(on_image=on_image)

  camera.start()

  sleep(5)
  camera.stop()

  del camera
  manager.release()



if __name__ == '__main__':
  main()