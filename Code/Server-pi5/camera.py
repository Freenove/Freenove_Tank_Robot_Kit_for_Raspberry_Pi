#!/usr/bin/python3
# Capture a JPEG while still running in the preview mode. When you
# capture to a file, the return value is the metadata for that image.
import time
from picamera2 import Picamera2, Preview
from libcamera import Transform
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(main={"size": (640, 480)},transform=Transform(hflip=1,vflip=1))
picam2.configure(preview_config)
picam2.start_preview(Preview.QTGL)
picam2.start()
time.sleep(2)
metadata = picam2.capture_file("image.jpg")
print(metadata)
picam2.close()