
from numbers import Number
from typing import Any, Callable, Dict,  Tuple
import PySpin
import statistics
from beartype import beartype

from disable_gc import disable_gc
from fuzzywuzzy import process



def suggest_node(nodemap, k, threshold=50):
  names = [node.GetName() for node in nodemap.GetNodes()]
  if k in names:  
    return "Node {} exists, but not available".format(k)
  
  nearest, score = process.extractOne(k, names)
  suggest = "" if score < threshold else ", did you mean '{}' ({})?".format(nearest, score)
  return f"Node {k} not available {suggest}"

class NodeException(RuntimeError):
  def __init__(self, msg):
    super(NodeException, self).__init__(msg)



node_type_mapping = {
   2: PySpin.CIntegerPtr,
   3: PySpin.CBooleanPtr,
   5: PySpin.CFloatPtr,
   9: PySpin.CEnumerationPtr
}

def get_node(nodemap:PySpin.INodeMap, node_name:str):
  node = nodemap.GetNode(node_name)
  if node is None:
    raise NodeException(suggest_node(nodemap, node_name))

  t = node.GetPrincipalInterfaceType()
  if t not in node_type_mapping:
    raise NodeException(f'Node type for {node_name} not supported {t}')
  return node_type_mapping[t](node)


def get_writable(nodemap:PySpin.INodeMap, node_name:str):
  node = get_node(nodemap, node_name)
  if not PySpin.IsAvailable(node):
    raise NodeException(suggest_node(nodemap, node_name))

  if not PySpin.IsWritable(node):
    raise NodeException('Node not writable {}. '.format(node_name))
  return node


def is_writable(nodemap:PySpin.INodeMap, node_name:str):
  node = get_node(nodemap, node_name)
  return PySpin.IsAvailable(node) and PySpin.IsWritable(node)
  
  
def get_readable(nodemap:PySpin.INodeMap, node_name:str):
  node = get_node(nodemap, node_name)
    
  if not PySpin.IsAvailable(node):
    raise NodeException(suggest_node(nodemap, node_name))

  if not PySpin.IsReadable(node):
    raise NodeException('Node not readable {}. '.format(node_name))
  return node

def is_readable(nodemap:PySpin.INodeMap, node_name:str):
  node = get_node(nodemap, node_name)
  return PySpin.IsAvailable(node) and PySpin.IsReadable(node)

def get_value(nodemap:PySpin.INodeMap, node_name:str):
  node = get_readable(nodemap, node_name)
  if isinstance(node, PySpin.CEnumerationPtr):
     return node.GetCurrentEntry().GetSymbolic()
  else:
    return node.GetValue()

def try_get_value(nodemap, node_name, default=None):
  try:
    return get_value(nodemap, node_name)
  except NodeException:
    return default


def set_value(nodemap:PySpin.INodeMap, node_name:str, value:Any):
  try:
    node = get_writable(nodemap, node_name)
    if isinstance(node, PySpin.CEnumerationPtr):
      # Retrieve entry node from enumeration node
      entry = node.GetEntryByName(value)
      if not PySpin.IsAvailable(entry):
          raise NodeException('Entry not available {} - {}. '.format(node_name, value))

      if not PySpin.IsReadable(entry):
          raise NodeException('Entry not readable {} - {} '.format(node_name, value))

      index = entry.GetValue()
      node.SetIntValue(index)

    elif isinstance(node, PySpin.CBooleanPtr):
      node.SetValue(bool(value))
    elif isinstance(node, PySpin.CFloatPtr):
      node.SetValue(float(value))
    elif isinstance(node, PySpin.CIntegerPtr):
      node.SetValue(int(value))
    
  except ValueError as e:
    raise NodeException(f"Invalid value {value} for node {node_name}: {e}")


@beartype
def set_bool(nodemap:PySpin.INodeMap, node_name:str, value:bool):
  return set_value(nodemap, node_name, value)

@beartype
def set_float(nodemap:PySpin.INodeMap, node_name:str, value:Number):
  return set_value(nodemap, node_name, value)

@beartype
def set_int(nodemap:PySpin.INodeMap, node_name:str, value:int):
  return set_value(nodemap, node_name, value)


@beartype
def set_enum(nodemap:PySpin.INodeMap, node_name:str, value:str):
  return set_value(nodemap, node_name, value)

def try_set_value(nodemap:PySpin.INodeMap, node_name:str, value):
  try:
      return set_value(nodemap, node_name, value)
  except PySpin.SpinnakerException as e:
      return get_value(nodemap, node_name)

@beartype
def try_set_bool(nodemap:PySpin.INodeMap, node_name:str, value:bool):
  return try_set_value(nodemap, node_name, value)

@beartype
def try_set_float(nodemap:PySpin.INodeMap, node_name:str, value:Number):
  return try_set_value(nodemap, node_name, value)

@beartype
def try_set_int(nodemap:PySpin.INodeMap, node_name:str, value:int):
  return try_set_value(nodemap, node_name, value)


@disable_gc
def camera_time_offset(cam:PySpin.Camera, get_time_sec:Callable[[], float], iters:int=50):
    """ Gets timestamp offset in seconds from camera to system clock """

    timestamp_offsets = []
    for i in range(iters):
        cam.TimestampLatch.Execute()

        # Compute timestamp offset in seconds; note that timestamp latch value is in seconds
        timestamp_offset = get_time_sec() - float(cam.TimestampLatchValue.GetValue()) / 1e9
        timestamp_offsets.append(timestamp_offset)

    # Return the median value
    return statistics.median(timestamp_offsets)



def execute(nodemap:PySpin.INodeMap, node_name:str):
    node = PySpin.CCommandPtr(nodemap.GetNode(node_name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        raise NodeException(suggest_node(nodemap, node_name))
    
    node.Execute(True)


def reset_camera(camera:PySpin.CameraPtr):
    camera.Init()
    nodemap = camera.GetNodeMap()
    execute(nodemap, "DeviceReset")  
    camera.DeInit()

def load_defaults(camera: PySpin.Camera):
    nodemap = camera.GetNodeMap()

    set_enum(nodemap, "UserSetSelector", "Default")
    execute(nodemap, "UserSetLoad")



def trigger(camera: PySpin.Camera):
    nodemap = camera.GetNodeMap()
    execute(nodemap, "TriggerSoftware")



def dict_item(d:Dict):
    k = next(iter(d)) # setting.keys()[0]
    v = d[k]
    return k, v


def get_camera_serial(cam : PySpin.Camera):
    nodemap_tldevice = cam.GetTLDeviceNodeMap()
    node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
    device_serial_number = node_device_serial_number.GetValue()
    return int(device_serial_number)


def validate_init(camera : PySpin.Camera):
    return camera.IsValid() and camera.IsInitialized()


def validate_streaming(camera : PySpin.Camera):
    return validate_init(camera) and camera.IsStreaming()


def get_image_size(camera : PySpin.Camera) -> Tuple[int, int]:
    node_map = camera.GetNodeMap()

    w = get_value(node_map, "Width")
    h = get_value(node_map, "Height")

    return (w, h)


def get_framerate_info(camera : PySpin.Camera):
  node_map = camera.GetNodeMap()

  is_free_running = get_value(node_map, "AcquisitionFrameRateEnable")
  max_framerate = get_value(node_map, "AcquisitionFrameRate")

  return max_framerate if is_free_running else None