import argparse

import torch
from taichi_image import bayer
from taichi_image.test.camera_isp import load_test_image
from tqdm import tqdm

from camera_driver.concurrent.taichi_queue import TaichiQueue
from camera_driver.concurrent.work_queue import WorkQueue
from camera_driver.data.encoding import ImageEncoding
from camera_driver.pipeline.config import ImageSettings
from camera_driver.pipeline.image.camera_image import CameraImage, CameraInfo
from camera_driver.pipeline.image.frame_processor import FrameProcessor


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("filename", help="Path to image file")
  parser.add_argument("--device", default="cuda", help="Device to use for processing")
  parser.add_argument("--resize_width", type=int, default=0, help="Resize width")
  parser.add_argument("--transform", type=str, default='none', help="Transformation to apply")
  parser.add_argument("--preload", action="store_true", help="Preload imges to cuda")
  parser.add_argument("--n", type=int, default=6, help="Number of cameras to test")
  parser.add_argument("--frames", type=int, default=300, help="Number of cameras to test")
  parser.add_argument("--no_compress", action="store_true", help="Disable compression")

  args = parser.parse_args()


  print(args)
  image_settings= ImageSettings(
      jpeg_quality=96,
      preview_size=200,
      resize_width=args.resize_width,
      tone_mapping="reinhard",
      tone_gamma= 1.0,
      tone_intensity= 1.0,
      color_adapt=0.0,
      light_adapt=0.5,
      transform=args.transform
  )

  test_packed, test_image  = TaichiQueue.run_sync(load_test_image, args.filename, bayer.BayerPattern.RGGB)
  test_packed = torch.from_numpy(test_packed)

  if args.preload:
      test_packed = test_packed.cuda()

  h, w, _ = test_image.shape


  encoding = ImageEncoding.Bayer_BGGR12
  camera_info = {f"{n}":CameraInfo(
      name="test{n}",
      serial="{n}",
      encoding = encoding,
      image_size=(w, h))

  for n in range(args.n)}

  frame_processor = FrameProcessor(camera_info, image_settings, device=torch.device(args.device))


  pbar = tqdm(total=int(args.frames))

  def on_frame(outputs):
    if not args.no_compress:

      for output in outputs:
        compressed = output.compressed
        preview = output.compressed_preview

    pbar.update(1)

  processor = WorkQueue("publisher", run=on_frame, num_workers=4, max_size=4)
  processor.start()


  images = {f"{n}":CameraImage(
    camera_name=f"test{n}",
    image_data=test_packed.clone(),
    image_size=(w, h),
    encoding=encoding,
    timestamp_sec=0.)
      for n in range(6) }

  frame_processor.bind(on_frame=on_frame)
      
  for _ in range(int(args.frames)):
    frame_processor.process(images)

  frame_processor.stop()
  processor.stop()

  TaichiQueue.stop()
  print("Finished")

if __name__ == "__main__":
  with torch.inference_mode():
    main()
