# camera_driver_python

## Install 

`pip install camera_driver_python`

Note - PyTorch is not included as a requirement and is assumed to be installed. Vendor specific camera libraries need to be installed separately.

### Backends

* Spinnaker - requires both system install of the `Spinnaker SDK` and also the python wheel providing `PySpin`

* IDS peak - requires system install plus python library which can be installed with `pip install ids_peak`


## Basic usage 

See `camera_driver/scripts/capture_images.py` for an example usage of the complete pipleine.


## Design

The library is broken into three main parts:

1) A set of abstractions for a specific camera vendor (`Manager`, `Camera` and `Buffer`) each of which 
have an implementation for a specific camera vendor, and implement a common interface for which to access, manipulate and capture frames asychronously. 

Each vendor library (of which there are two `driver.peak` and `driver.spinnaker` currently), provides implementations for the following interfaces (specified by a set of abstract classes in `driver.interface`)

 * A `Manager` class, which provides an interface to find and initialise cameras from a specific vendor.
 *  A `Camera` class provides an interface to control a particular camera, set it's settings and capture frames asynchronously. 
 * A `Buffer` class provides image data in a consistent way, a numpy interface provides the raw data which can then be processed as required, but must be copied before `Buffer.release` is called.



2) Camera agnostic utilities for dealing with groups of cameras `camera_group.CameraSet`, for setting common settings, and `camera_group.SyncHandler` for grouping frames which are collected asynchronously from multiple triggered cameras, but need grouping together.


3) A specific image processing `pipeline` for capturing and processing 12 bit HDR images. This utilizes `taichi_image` and torch for image processing, and is accesed through the high level interface `pipeline.CameraPipeline` for taking images, synchronizing them and processing them.



