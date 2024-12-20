from enum import Enum


class BayerPattern(Enum):
  BGGR = "bggr"
  RGGB = "rggb"
  GBRG = "gbrg"
  GRBG = "grbg"


class ImageEncoding(Enum):
  Bayer_BGGR8 = "bayer_bggr8"
  Bayer_RGGB8 = "bayer_rggb8"
  Bayer_GBRG8 = "bayer_gbrg8"
  Bayer_GRBG8 = "bayer_grbg8"
  Bayer_BGGR12 = "bayer_bggr12"
  Bayer_RGGB12 = "bayer_rggb12"
  Bayer_GBRG12 = "bayer_gbrg12"
  Bayer_GRBG12 = "bayer_grbg12"

  Bayer_RGGB12_IDS = "bayer_rggb12p_ids"
  Bayer_BGGR12_IDS = "bayer_bggr12p_ids"
  Bayer_GBRG12_IDS = "bayer_gbrg12p_ids"
  Bayer_GRBG12_IDS = "bayer_grbg12p_ids"



  Bayer_BGGR16 = "bayer_bggr16"
  Bayer_RGGB16 = "bayer_rggb16"
  Bayer_GBRG16 = "bayer_gbrg16"
  Bayer_GRBG16 = "bayer_grbg16"


class EncodingType(Enum):
  Packed8 = "packed8"
  Packed12 = "packed12"
  Packed12_IDS = "packed12_ids"
  Packed16 = "packed16"



def encoding_type(encoding):
  if encoding in [ImageEncoding.Bayer_BGGR8, ImageEncoding.Bayer_RGGB8, ImageEncoding.Bayer_GBRG8, ImageEncoding.Bayer_GRBG8]:
    return EncodingType.Packed8
  elif encoding in [ImageEncoding.Bayer_BGGR12, ImageEncoding.Bayer_RGGB12, ImageEncoding.Bayer_GBRG12, ImageEncoding.Bayer_GRBG12]:
    return EncodingType.Packed12
  elif encoding in [ImageEncoding.Bayer_RGGB12_IDS, ImageEncoding.Bayer_BGGR12_IDS, ImageEncoding.Bayer_GBRG12_IDS, ImageEncoding.Bayer_GRBG12_IDS]:
    return EncodingType.Packed12_IDS
  elif encoding in [ImageEncoding.Bayer_BGGR16, ImageEncoding.Bayer_RGGB16, ImageEncoding.Bayer_GBRG16, ImageEncoding.Bayer_GRBG16]:
    return EncodingType.Packed16
  else:
    raise ValueError(f"Encoding not implemented {encoding}")


def bayer_pattern(encoding):
  if encoding in [ImageEncoding.Bayer_BGGR8, ImageEncoding.Bayer_BGGR12, ImageEncoding.Bayer_BGGR12_IDS,  ImageEncoding.Bayer_BGGR16]:
    return BayerPattern.BGGR
  elif encoding in [ImageEncoding.Bayer_RGGB8, ImageEncoding.Bayer_RGGB12, ImageEncoding.Bayer_RGGB12_IDS, ImageEncoding.Bayer_RGGB16]:
    return BayerPattern.RGGB
  elif encoding in [ImageEncoding.Bayer_GBRG8, ImageEncoding.Bayer_GBRG12, ImageEncoding.Bayer_GBRG12_IDS, ImageEncoding.Bayer_GBRG16]:
    return BayerPattern.GBRG
  elif encoding in [ImageEncoding.Bayer_GRBG8, ImageEncoding.Bayer_GRBG12, ImageEncoding.Bayer_GRBG12_IDS, ImageEncoding.Bayer_GRBG16]:
    return BayerPattern.GRBG
  else:
    raise ValueError(f"Encoding not implemented {encoding}")
  



camera_encodings = dict(
    BayerRG8 = ImageEncoding.Bayer_RGGB8,
    BayerBG8 = ImageEncoding.Bayer_BGGR8,
    BayerGR8 = ImageEncoding.Bayer_GRBG8,
    BayerGB8 = ImageEncoding.Bayer_GBRG8,
    
    BayerRG12p = ImageEncoding.Bayer_RGGB12,
    BayerBG12p = ImageEncoding.Bayer_BGGR12,
    BayerGR12p = ImageEncoding.Bayer_GRBG12,
    BayerGB12p = ImageEncoding.Bayer_GBRG12,

    BayerRG12g24IDS = ImageEncoding.Bayer_RGGB12_IDS,
    BayerBG12g24IDS = ImageEncoding.Bayer_BGGR12_IDS,
    BayerGR12g24IDS = ImageEncoding.Bayer_GRBG12_IDS,
    BayerGB12g24IDS = ImageEncoding.Bayer_GBRG12_IDS,
    

    BayerRG16 = ImageEncoding.Bayer_RGGB16,
    BayerBG16 = ImageEncoding.Bayer_BGGR16,
    BayerGR16 = ImageEncoding.Bayer_GRBG16,
    BayerGB16 = ImageEncoding.Bayer_GBRG16,
)
