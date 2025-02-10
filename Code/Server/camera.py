import time
from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder, JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform
from threading import Condition
import io

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()     # Initialize the condition variable for thread synchronization

    def write(self, buf):
        with self.condition:
            self.frame = buf             # Update the frame buffer with new data
            self.condition.notify_all()  # Notify all waiting threads that new data is available

class Camera:
    def __init__(self, preview_size=(640, 480), hflip=True, vflip=True, stream_size=(400, 300)):
        self.camera = Picamera2()              # Initialize the Picamera2 object
        self.transform = Transform(hflip=1 if hflip else 0, vflip=1 if vflip else 0)  # Set the transformation for flipping the image
        preview_config = self.camera.create_preview_configuration(main={"size": preview_size}, transform=self.transform)  # Create the preview configuration
        self.camera.configure(preview_config)  # Configure the camera with the preview settings
        
        # Configure video stream
        self.stream_size = stream_size             # Set the size of the video stream
        self.stream_config = self.camera.create_video_configuration(main={"size": stream_size}, transform=self.transform)  # Create the video configuration
        self.streaming_output = StreamingOutput()  # Initialize the streaming output object
        self.streaming = False                     # Initialize the streaming flag

    def start_image(self):
        self.camera.start_preview(Preview.QTGL)  # Start the camera preview using the QTGL backend
        self.camera.start()                      # Start the camera

    def save_image(self, filename):
        metadata = self.camera.capture_file(filename)  # Capture an image and save it to the specified file
        return metadata                                # Return the metadata of the captured image

    def start_stream(self, filename=None):
        if not self.streaming:
            if self.camera.started:
                self.camera.stop()                          # Stop the camera if it is currently running
            
            self.camera.configure(self.stream_config)       # Configure the camera with the video stream settings
            if filename:
                encoder = H264Encoder()                     # Use H264 encoder for video recording
                output = FileOutput(filename)               # Set the output file for the recorded video
            else:
                encoder = JpegEncoder()                     # Use Jpeg encoder for streaming
                output = FileOutput(self.streaming_output)  # Set the streaming output object
            self.camera.start_recording(encoder, output)    # Start recording or streaming
            self.streaming = True                           # Set the streaming flag to True

    def stop_stream(self):
        if self.streaming:
            self.camera.stop_recording()  # Stop the recording or streaming
            self.streaming = False        # Set the streaming flag to False

    def get_frame(self):
        with self.streaming_output.condition:
            self.streaming_output.condition.wait()  # Wait for a new frame to be available
            return self.streaming_output.frame      # Return the current frame

    def save_video(self, filename, duration=10):
        self.start_stream(filename)  # Start the video recording
        time.sleep(duration)         # Record for the specified duration
        self.stop_stream()           # Stop the video recording

    def close(self):
        if self.streaming:
            self.stop_stream()  # Stop the streaming if it is active
        self.camera.close()     # Close the camera

if __name__ == '__main__':
    picam2 = Camera()                        # Create a Camera instance

    print("view image...")
    picam2.start_image()                     # Start the camera preview
    time.sleep(1)                            # Wait for 1 second
    
    print("capture image...")
    picam2.save_image(filename="image.jpg")  # Capture and save an image
    time.sleep(1)                            # Wait for 1 second

    print("stream video...")
    picam2.start_stream()                    # Start the video stream
    time.sleep(3)                            # Stream for 3 seconds
    
    print("stop video...")
    picam2.stop_stream()                     # Stop the video stream
    time.sleep(1)                            # Wait for 1 second

    print("save video...")
    picam2.save_video("video.h264", duration=3)  # Save a video for 3 seconds
    time.sleep(1)                            # Wait for 1 second
    
    print("close camera...")
    picam2.close()                           # Close the camera