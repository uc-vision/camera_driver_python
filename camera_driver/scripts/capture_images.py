
from collections import deque
from datetime import datetime
import logging
from pathlib import Path
from queue import Queue
import traceback
from beartype.typing import Dict, Tuple
from camera_driver.pipeline.unsync_pipeline import CameraPipelineUnsync
from omegaconf import OmegaConf
import cv2

from argparse import ArgumentParser

from camera_driver.concurrent import WorkQueue
from camera_driver.pipeline import CameraPipeline, CameraInfo, ImageOutputs, CameraPipelineConfig


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


def view_images(queue:Queue, camera_info:Dict[str, CameraInfo]):
  cv2.namedWindow("image", cv2.WINDOW_NORMAL)
  cv2.resizeWindow("image", 800, 600)

  while True:
    image_group:Dict[str, ImageOutputs] = queue.get()
    previews = [image_group[k].preview.cpu().numpy() 
                for k in camera_info.keys()]
    
    cv2.imshow("image", cv2.cvtColor(cv2.hconcat(previews), cv2.COLOR_RGB2BGR))
    cv2.waitKey(1)


def main():

  parser = ArgumentParser()
  parser.add_argument("--config", nargs='+', type=str, required=True)

  parser.add_argument("--write", type=str)
  parser.add_argument("--show", action="store_true")
  parser.add_argument("--no_sync", action="store_true")

  args = parser.parse_args()

  config = CameraPipelineConfig.load_yaml(*args.config)
  logger.info(OmegaConf.to_yaml(config))


  def get_timestamp():
    return datetime.now().timestamp()
  
  if args.no_sync:
    pipeline = CameraPipelineUnsync(config, logger, query_time=get_timestamp)
  else:
    pipeline = CameraPipeline(config, logger, query_time=get_timestamp)

  if args.write:
    writer = ImageWriter(args.write, num_cameras=len(config.cameras))

    pipeline.bind(on_image_set=writer.write_images)
    pipeline.bind(on_stopped=writer.stop) 


  queue = Queue()
  def on_group(group:Dict[str, ImageOutputs]):
    queue.put(group)

  pipeline.bind(on_image_set=on_group)

  try:
    pipeline.start()

    if args.show:
      view_images(queue, pipeline.camera_info)

    else:
      
      recieved = {k:deque(maxlen=20) for k in pipeline.camera_info.keys()}
      time = get_timestamp()
      while True:
        image_group:Dict[str, ImageOutputs] = queue.get()
        for k, image in image_group.items():
          recieved[k].append(image.timestamp_sec)

        def format_rate(times):
          rate = 0.0 if len(times) < 2 else (len(times) - 1) / (times[-1] - times[0])
          return f"{rate:.2f}"
        
        rates = {k:format_rate(times) for k, times in recieved.items()}
        if get_timestamp() - time > 2:
          logger.info(rates)
          time = get_timestamp()



  except Exception as e:
    logger.error(traceback.format_exc())

  finally:
    pipeline.stop()
    pipeline.release()

  




    
if __name__ == '__main__':
  main()