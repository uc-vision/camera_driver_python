
from datetime import datetime
import logging
from pathlib import Path
from time import sleep
from typing import Dict, Tuple
from omegaconf import OmegaConf


from argparse import ArgumentParser

from camera_driver.concurrent.taichi_queue import TaichiQueue
from camera_driver.concurrent.work_queue import WorkQueue
from camera_driver.config import CameraPipelineConfig
from camera_driver.image.image_outputs import ImageOutputs
from camera_driver.pipeline import CameraPipeline


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')


class ImageWriter():
  def __init__(self, output_dir:str, num_cameras:int=1):
    self.output_dir = Path(output_dir)
    self.counter = 0

    self.work_queue = WorkQueue("image_writer", self.process_image, logger=logger, 
                                num_workers=2, max_size=num_cameras)
    self.work_queue.start()
    

  def write_images(self, images:Dict[str, ImageOutputs]):
    for name, image in images.items():
      self.work_queue.enqueue((image, self.counter))

    self.counter = self.counter + 1


  def process_image(self, image_counter:Tuple[ImageOutputs, int]):
    image, counter = image_counter

    camera_dir = self.output_dir/image.camera_name
    camera_dir.mkdir(parents=True, exist_ok=True)

    with open(camera_dir / f"image_{counter:04d}.jpg", "wb") as f:
      f.write(image.compressed)


  def stop(self):
    self.work_queue.stop()





def main():

  parser = ArgumentParser()
  parser.add_argument("--config", type=str, required=True)
  parser.add_argument("--settings", type=str, required=True)

  parser.add_argument("--write", type=str)
  args = parser.parse_args()

  config = CameraPipelineConfig.load_yaml(args.config)
  logger.info(OmegaConf.to_yaml(config))

  camera_settings = OmegaConf.to_container(OmegaConf.load(args.settings))

  def get_timestamp():
    return datetime.now().timestamp()
  
  pipeline = CameraPipeline(config, camera_settings, logger, query_time=get_timestamp)

  if args.write:
    writer = ImageWriter(args.write, num_cameras=len(config.cameras))

    pipeline.bind(on_image_set=writer.write_images)
    pipeline.bind(on_stopped=writer.stop) 

  def on_group(group:Dict[str, ImageOutputs]):
    print(group)

  pipeline.bind(on_image_set=on_group)

  try:
    pipeline.start()

    while True:
      sleep(1)


  finally:
    pipeline.stop()
    pipeline.release()


    TaichiQueue.stop()


    
if __name__ == '__main__':
  main()