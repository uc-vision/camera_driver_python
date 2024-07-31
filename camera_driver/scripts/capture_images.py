
from dataclasses import replace
from datetime import datetime
import logging
from queue import Queue
from time import sleep
import traceback
from beartype.typing import Dict
from camera_driver.scripts.util import ImageWriter, RateMonitor, view_images
from omegaconf import OmegaConf

from argparse import ArgumentParser

from camera_driver.pipeline.unsync_pipeline import CameraPipelineUnsync
from camera_driver.pipeline import CameraPipeline, ImageOutputs, CameraPipelineConfig






def main():

  parser = ArgumentParser()
  parser.add_argument("--config", nargs='+', type=str, required=True)
  parser.add_argument("--log_level", default="info", type=str, choices=["debug", "info", "warning", "error"])


  parser.add_argument("--write", type=str)
  parser.add_argument("--show", action="store_true")
  parser.add_argument("--no_sync", action="store_true")
  parser.add_argument("--reset", action="store_true")

  args = parser.parse_args()

  logger = logging.getLogger(__name__)
  logging.basicConfig(level=logging.getLevelName(args.log_level.upper()), format='%(message)s')

  config = CameraPipelineConfig.load_yaml(*args.config)
  logger.info(OmegaConf.to_yaml(config))


  if args.reset:
    config = replace(config, reset_cycle=True)

  def get_timestamp():
    return datetime.now().timestamp()
  
  if args.no_sync:
    pipeline = CameraPipelineUnsync(config, logger, query_time=get_timestamp)
  else:
    pipeline = CameraPipeline(config, logger, query_time=get_timestamp)

  if args.write:
    writer = ImageWriter(args.write, num_cameras=len(pipeline.camera_info), logger=logger)

    pipeline.bind(on_image_set=writer.write_images)
    pipeline.bind(on_stopped=writer.stop) 


  monitor = RateMonitor(pipeline, logger, interval=2.0)

  try:

    pipeline.start()

    if args.show:
      queue = Queue(len(pipeline.camera_info))
      def on_group(group:Dict[str, ImageOutputs]):
        queue.put(group)

      pipeline.bind(on_image_set=on_group)

      view_images(queue, pipeline.camera_info, preview_width=config.parameters.preview_size)

    else:
      while True:
        sleep(1)


  except Exception as e:
    logger.error(traceback.format_exc())

  finally:
    pipeline.stop()
    pipeline.release()

  




    
if __name__ == '__main__':
  main()