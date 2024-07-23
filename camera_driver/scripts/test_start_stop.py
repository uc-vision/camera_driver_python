
from dataclasses import replace
from datetime import datetime
import logging
from time import sleep
import traceback
from camera_driver.scripts.util import Counter
from omegaconf import OmegaConf

from argparse import ArgumentParser

from camera_driver.pipeline.unsync_pipeline import CameraPipelineUnsync
from camera_driver.pipeline import CameraPipeline, CameraPipelineConfig


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def main():

  parser = ArgumentParser()
  parser.add_argument("--config", nargs='+', type=str, required=True)
  parser.add_argument("--no_sync", action="store_true")
  parser.add_argument("--reset", action="store_true")


  args = parser.parse_args()

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


  try:
    while True:
        with Counter(pipeline) as counter:
          pipeline.start()
          sleep(2)
          pipeline.stop()
          
          logger.info(f"Received: {counter.recieved}")
        sleep(1)

  except Exception as e:
    logger.error(traceback.format_exc())

  finally:
    pipeline.stop()
    pipeline.release()


    
if __name__ == '__main__':
  main()