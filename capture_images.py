
from datetime import datetime
import logging
from typing import Dict
from omegaconf import OmegaConf


from argparse import ArgumentParser

from camera_driver.config import CameraPipelineConfig, load_structured
from camera_driver.image.camera_image import CameraImage
from camera_driver.pipeline import CameraPipeline


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def main():

  parser = ArgumentParser()
  parser.add_argument("--config", type=str, required=True)
  parser.add_argument("--settings", type=str, required=True)
  args = parser.parse_args()

  config = load_structured(args.config, CameraPipelineConfig)
  logger.info(OmegaConf.to_yaml(config))

  camera_settings = OmegaConf.load(args.settings)

  def get_timestamp():
    return datetime.now().timestamp()
  
  pipeline = CameraPipeline(config, camera_settings, logger, query_time=get_timestamp())

  def on_group(group:Dict[str, CameraImage]):
    print(group)

  pipeline.bind("on_image_group", on_group)
  pipeline.start()
  # offsets = camera_set.compute_clock_offsets(get_timestamp)
  # print(offsets)


  # try:


  #   #   buffer.release()

  #   # camera_set.bind(on_buffer=on_buffer)
  #   camera_set.start()

  #   sleep(5)

  # finally:
  #   camera_set.release()


    
if __name__ == '__main__':
  main()