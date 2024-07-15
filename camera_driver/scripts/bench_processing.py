import argparse
import logging

import torch
from taichi_image import bayer
from taichi_image.test.camera_isp import load_test_image
from tqdm import tqdm

from camera_driver.concurrent.taichi_queue import TaichiQueue
from camera_driver.concurrent.work_queue import WorkQueue
from camera_driver.data.encoding import ImageEncoding

from camera_driver import pipeline

def main():
  logger = logging.getLogger(__name__)
  logging.basicConfig(level=logging.DEBUG, format='%(message)s')



  parser = argparse.ArgumentParser()
  parser.add_argument("filename", help="Path to image file")
  parser.add_argument("--device", default="cuda", help="Device to use for processing")
  parser.add_argument("--resize_width", type=int, default=0, help="Resize width")
  parser.add_argument("--transform", type=str, default='none', help="Transformation to apply")
  parser.add_argument("--preload", action="store_true", help="Preload imges to cuda")
  parser.add_argument("--n", type=int, default=12, help="Number of cameras to test")
  parser.add_argument("--frames", type=int, default=300, help="Number of cameras to test")
  parser.add_argument("--no_compress", action="store_true", help="Disable compression")

  args = parser.parse_args()


  logging.info(str(args))
  image_settings= pipeline.ImageSettings(
      jpeg_quality=94,
      preview_size=200,
      resize_width=args.resize_width,
      tone_mapping=pipeline.ToneMapper.reinhard,
      tone_gamma= 1.0,
      tone_intensity= 1.0,
      color_adapt=0.0,
      light_adapt=0.5,
      transform=pipeline.Transform[args.transform]
  )

  test_packed, test_image  = TaichiQueue.run_sync(load_test_image, 
                                args.filename, bayer.BayerPattern.RGGB)
  test_packed = torch.from_numpy(test_packed)

  if args.preload:
      test_packed = test_packed.cuda()

  h, w, _ = test_image.shape
  logger.info(f"Benchmarking on {args.filename}: {w}x{h} with {args.n} cameras")

  encoding = ImageEncoding.Bayer_BGGR12
  camera_info = {f"cam{n}":pipeline.CameraInfo(
      name="cam{n}",
      serial="{n}"*5,
      encoding = encoding,
      image_size=(w, h))

  for n in range(args.n)}

  frame_processor = pipeline.FrameProcessor(camera_info, 
              settings = image_settings,
              device=torch.device(args.device), 
              logger=logger)


  pbar = tqdm(total=int(args.frames))

  def on_frame(outputs):
    if not args.no_compress:

      for k, output in outputs.items():
        compressed = output.compressed
        preview = output.compressed_preview

    pbar.update(1)

  processor = WorkQueue("publisher", run=on_frame, num_workers=4, max_size=4, logger=logger)
  processor.start()


  images = {f"cam{n}":pipeline.CameraImage(
    camera_name=f"cam{n}",
    image_data=test_packed.clone(),
    image_size=(w, h),
    encoding=encoding,
    timestamp_sec=0.)
      for n in range(args.n) }

  frame_processor.bind(on_frame=on_frame)
      
  for _ in range(int(args.frames)):
    frame_processor.process_image_set(images)

  frame_processor.stop()
  processor.stop()

  TaichiQueue.stop()
  print("Finished")

if __name__ == "__main__":
  with torch.inference_mode():
    main()
