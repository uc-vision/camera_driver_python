# from camera_driver.harvester import HarvesterManager

# def main():

#   manager = HarvesterManager('/usr/lib/ids/cti/ids_u3vgentl.cti')
#   print(manager.camera_serials())


import logging
from time import sleep

import torch
from camera_driver.peak import Manager
from camera_driver.peak.buffer import Buffer


logger = logging.getLogger(__name__)


def main():

  manager = Manager(logger)
  print(manager.camera_serials())

  serial = manager.camera_serials()[0]
  camera = manager.init_camera("camera", serial)

  def on_image(buffer:Buffer):

    image = buffer.image(device=torch.device("cuda", 0))
    print(image)

    buffer.release()


  camera.bind(on_image=on_image)

  camera.start()

  sleep(5)
  camera.stop()



if __name__ == '__main__':
  main()