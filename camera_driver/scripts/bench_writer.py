

import argparse
import logging
from pathlib import Path
from tqdm import tqdm

from camera_driver.concurrent.work_queue import WorkQueue


def write_file(item):
  data, filename = item
  with open(filename, 'wb') as f:
    f.write(data)

def main():
  args = argparse.ArgumentParser()
  args.add_argument('input', type=str, help='Input file')
  args.add_argument('output', type=str, help='Output folder')
  args.add_argument('num_threads', type=int, help='Number of threads')
  args.add_argument('n', type=int, default=10000, help='Number of writes')

  args = args.parse_args()

  logger = logging.getLogger('bench_writer')
  logger.setLevel(logging.INFO)
  queue = WorkQueue(write_file, logger, num_workers=args.num_threads)
  queue.start()
  

  # read file binary
  with open(args.input, 'rb') as f:
    data = f.read()

  output = Path(args.output)
  output.mkdir(exist_ok=True, parents=True)

  for i in tqdm(range(args.n)):
    queue.enqueue((data, output / f'file_{i:04d}'))


if __name__ == '__main__':
  main()