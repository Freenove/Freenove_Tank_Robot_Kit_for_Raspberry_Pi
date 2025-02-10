import sys                                             # Import the sys module for system operations
import struct                                          # Import the struct module for packing and unpacking binary data
import time                                            # Import the time module for timing functions
import signal                                          # Import the signal module for handling signals
from PyQt5.QtWidgets import QMainWindow, QApplication  # Import QMainWindow and QApplication from PyQt5.QtWidgets
from PyQt5.QtCore import QTimer                        # Import QTimer from PyQt5.QtCore
from server_ui import Ui_server_ui                     # Import the UI class from the server_ui module

from server import TankServer                           # Import the TankServer class from the server module
import threading                                       # Import the threading module for creating threads
import multiprocessing                                 # Import the multiprocessing module for creating processes
from message import MessageParser                      # Import the MessageParser class from the message module
from command import Command                             # Import the Command class from the command module
from led import Led                                    # Import the Led class from the led module
from camera import Camera                              # Import the Camera class from the camera module
from car import Car                                    # Import the Car class from the car module

class mywindow(QMainWindow, Ui_server_ui):
    def __init__(self):
        self.app = QApplication(sys.argv)              # Initialize the QApplication with command-line arguments
        super(mywindow, self).__init__()               # Call the superclass constructor
        self.setupUi(self)                             # Set up the user interface
        self.ui_button_state = True                    # Initialize the UI button state
        self.config_task()                             # Configure tasks
        self.Button_Server.clicked.connect(self.on_pushButton_handle)  # Connect the button click event to the handler
        if self.ui_button_state:
            self.on_pushButton_handle()                                # Handle the button click if the UI button state is True
        self.app.lastWindowClosed.connect(self.close_application)      # Connect the last window closed event to the close application method
        signal.signal(signal.SIGINT, self.signal_handler)              # Set up a signal handler for SIGINT (Ctrl+C)
        
        self.timer = QTimer(self)                       # Create a QTimer object
        self.timer.timeout.connect(self.check_signals)  # Connect the timer timeout event to the check signals method
        self.timer.start(100)                           # Start the timer with an interval of 100 milliseconds

    def config_task(self):
        self.tcp_server = TankServer()                 # Initialize the TCP server
        self.command = Command()                       # Initialize the command object
        self.led = Led()                               # Initialize the LED object
        self.car = Car()                               # Initialize the car object
        self.camera = Camera(stream_size=(400, 300))   # Initialize the camera with a stream size of 400x300
        self.queue_cmd = multiprocessing.Queue()       # Create a queue for commands
        self.cmd_parser = MessageParser()              # Initialize the command parser
        self.queue_led = multiprocessing.Queue()       # Create a queue for LED commands
        self.led_parser = MessageParser()              # Initialize the LED parser

        self.cmd_thread = None                         # Initialize the command thread
        self.video_thread = None                       # Initialize the video thread
        self.car_thread = None                         # Initialize the car thread
        self.led_process = None                        # Initialize the LED process
        self.action_process = None                     # Initialize the action process
        self.cmd_thread_is_running = False             # Initialize the command thread running state
        self.video_thread_is_running = False           # Initialize the video thread running state
        self.car_thread_is_running = False             # Initialize the car thread running state
        self.led_process_is_running = False            # Initialize the LED process running state
        self.action_process_is_running = False         # Initialize the action process running state
        self.car_mode = 1                              # Initialize the car mode
        self.car_last_mode = 1                         # Initialize the last car mode
        self.left_wheel_speed = 0                      # Initialize the left wheel speed
        self.right_wheel_speed = 0                     # Initialize the right wheel speed

    def stop_car(self):
        self.led.colorWipe([0, 0, 0])                  # Turn off the LEDs
        self.camera.stop_stream()                      # Stop the camera stream
        self.camera.close()                            # Close the camera
        self.car.close()                               # Close the car

    def on_pushButton_handle(self):
        if self.label.text() == "Server Off":
            self.label.setText("Server On")            # Change the label text to "Server On"
            self.Button_Server.setText("Off")          # Change the button text to "Off"
            self.tcp_server.startTcpServer()           # Start the TCP server
            self.set_threading_cmd_receive(True)       # Start the command receive thread
            self.set_threading_video_send(True)        # Start the video send thread
            self.set_threading_car_task(True)          # Start the car task thread
            self.set_process_led_running(True)         # Start the LED process
        elif self.label.text() == 'Server On':
            self.label.setText("Server Off")           # Change the label text to "Server Off"
            self.Button_Server.setText("On")           # Change the button text to "On"
            self.tcp_server.stopTcpServer()            # Stop the TCP server
            self.set_threading_cmd_receive(False)      # Stop the command receive thread
            self.set_threading_video_send(False)       # Stop the video send thread
            self.set_threading_car_task(False)         # Stop the car task thread
            self.set_process_led_running(False)        # Stop the LED process
            self.tcp_server = TankServer()             # Reinitialize the TCP server

    def set_threading_cmd_receive(self, state, close_time=0.3):
        if self.cmd_thread is None:
            buf_state = False                          # Check if the command thread is None
        else:
            buf_state = self.cmd_thread.is_alive()     # Check if the command thread is alive
        if state != buf_state:
            if state:
                self.cmd_thread_is_running = True      # Set the command thread running state to True
                self.cmd_thread = threading.Thread(target=self.threading_cmd_receive)  # Create a new command receive thread
                self.cmd_thread.start()                # Start the command receive thread
            else:
                self.cmd_thread_is_running = False     # Set the command thread running state to False
                if self.cmd_thread is not None:
                    self.cmd_thread.join(close_time)   # Wait for the command thread to finish
                    self.cmd_thread = None             # Set the command thread to None

    def threading_cmd_receive(self):
        while self.cmd_thread_is_running:
            cmd_queue = self.tcp_server.readDataFromCmdServer()  # Read data from the command server
            if cmd_queue.qsize() > 0:
                client_address, all_message = cmd_queue.get()    # Get the client address and message from the queue
                main_message = all_message.strip()               # Strip any leading/trailing whitespace from the message
                if "\n" in main_message:
                    for msg in main_message.split("\n"):
                        self.queue_cmd.put(msg)                  # Put each message into the command queue
                else:
                    self.queue_cmd.put(main_message)             # Put the message into the command queue
            while not self.queue_cmd.empty():
                msg = self.queue_cmd.get()                       # Get a message from the command queue
                self.cmd_parser.clearParameters()                # Clear the parameters in the command parser
                self.cmd_parser.parser(msg)                      # Parse the message
                # print(self.cmd_parser.stringParameter)         # Print the parsed string parameters (commented out)
                if self.cmd_parser.commandString == self.command.CMD_LED:
                    self.queue_led.put(msg)                      # Put LED commands into the LED queue
                else:
                    if self.cmd_parser.commandString == self.command.CMD_SONIC:
                        pass                                                        # Placeholder for sonic commands
                    elif self.cmd_parser.commandString == self.command.CMD_SERVO:
                        if self.car_mode == 1 or self.car_mode == 2:   
                            servo_index = int(self.cmd_parser.intParameter[0])      # Get the servo index
                            servo_angle = int(self.cmd_parser.intParameter[1])      # Get the servo angle
                            self.car.servo.setServoAngle(servo_index, servo_angle)  # Set the servo angle
                        else:
                            print("You can control the servo only in Move mode and Sonar mode")      # Print a message if the mode is not correct
                    elif self.cmd_parser.commandString == self.command.CMD_MOTOR:
                        self.left_wheel_speed = int(self.cmd_parser.intParameter[0])                 # Get the left wheel speed
                        self.right_wheel_speed = int(self.cmd_parser.intParameter[1])                # Get the right wheel speed
                        self.car.motor.setMotorModel(self.left_wheel_speed, self.right_wheel_speed)  # Set the motor model
                    elif self.cmd_parser.commandString == self.command.CMD_MODE:
                        if self.car.infrared_run_stop == False:   
                            self.car.infrared_run_stop = True       # Set the infrared run stop state
                            time.sleep(0.1)                         # Sleep for 0.1 seconds
                        if self.cmd_parser.intParameter[0] == 0:
                            self.car_mode = 1                       # Set the car mode to 1
                            self.left_wheel_speed = 0               # Set the left wheel speed to 0
                            self.right_wheel_speed = 0              # Set the right wheel speed to 0
                            self.car.motor.setMotorModel(self.left_wheel_speed, self.right_wheel_speed)  # Set the motor model
                        elif self.cmd_parser.intParameter[0] == 1:
                            self.car_mode = 2                       # Set the car mode to 2
                        elif self.cmd_parser.intParameter[0] == 2:
                            self.car_mode = 3                       # Set the car mode to 3
                            self.car.infrared_run_stop = False      # Set the infrared run stop state to False
                        self.car_last_mode = self.car_mode          # Update the last car mode
                    elif self.cmd_parser.commandString == self.command.CMD_ACTION:
                        if self.car.infrared_run_stop == False:
                            self.car.infrared_run_stop = True       # Set the infrared run stop state
                            time.sleep(0.1)                         # Sleep for 0.1 seconds
                        if self.cmd_parser.intParameter[0] == 0:
                            self.car_mode = 4                       # Set the car mode to 4
                        elif self.cmd_parser.intParameter[0] == 1:
                            self.car_mode = 5                       # Set the car mode to 5
                        elif self.cmd_parser.intParameter[0] == 2:
                            self.car_mode = 6                       # Set the car mode to 6
            if self.queue_cmd.empty():
                time.sleep(0.001)                                   # Sleep for 0.001 seconds if the command queue is empty
      
    def set_threading_car_task(self, state, close_time=0.3):
        if self.car_thread is None: 
            buf_state = False                         # Check if the car thread is None
        else:
            buf_state = self.car_thread.is_alive()    # Check if the car thread is alive
        if state != buf_state:
            if state:
                self.car_thread_is_running = True     # Set the car thread running state to True
                self.car_thread = threading.Thread(target=self.threading_car_task)  # Create a new car task thread
                self.car_thread.start()               # Start the car task thread
            else:
                self.car_thread_is_running = False    # Set the car thread running state to False
                if self.car_thread is not None:
                    self.car_thread.join(close_time)  # Wait for the car thread to finish
                    self.car_thread = None            # Set the car thread to None
    
    def threading_car_task(self):
        while self.car_thread_is_running:
            if self.car_mode == 1:
                distance = self.car.sonic.get_distance()
                if self.tcp_server.get_cmd_server_busy() == False:
                    self.tcp_server.set_cmd_server_busy(True)
                    self.tcp_server.sendDataToCmdClinet("CMD_SONIC#{:.2f}".format(distance))
                    self.tcp_server.set_cmd_server_busy(False)
                time.sleep(1)                                                     # Sleep for 0.1 seconds if the car mode is 1
            elif self.car_mode == 2:
                self.car.mode_ultrasonic()                                        # Set the car mode to ultrasonic
                distance = self.car.sonic.get_distance()
                if self.tcp_server.get_cmd_server_busy() == False:
                    self.tcp_server.set_cmd_server_busy(True)
                    self.tcp_server.sendDataToCmdClinet("CMD_SONIC#{:.2f}".format(distance))
                    self.tcp_server.set_cmd_server_busy(False)
            elif self.car_mode == 3:
                self.car.mode_infrared()                                          # Set the car mode to infrared

            elif self.car_mode == 4:
                self.car.mode_clamp(0)                                            # Set the car mode to clamp stop
                self.car_mode = self.car_last_mode                                # Update the car mode to the last mode
                self.tcp_server.sendDataToCmdClinet("CMD_ACTION#0\r\n")           # Send the action command to the client
                print("clamp stop...")                                            # Print a message
            elif self.car_mode == 5:
                self.car.set_mode_clamp(1)                                        # Set the car mode to clamp up
                while self.car_thread_is_running and self.car_mode == 5:
                    if self.car.get_mode_clamp() == 1:
                        self.car.mode_clamp()                                     # Set the car mode to clamp
                        print("clamp up...")                                      # Print a message
                    elif self.car.get_mode_clamp() == 0:
                        self.car_mode = self.car_last_mode                        # Update the car mode to the last mode
                        self.tcp_server.sendDataToCmdClinet("CMD_ACTION#10\r\n")  # Send the action command to the client
                        print("clamp up stop")                                    # Print a message
                        break
            elif self.car_mode == 6:
                self.car.set_mode_clamp(2)                                        # Set the car mode to clamp down
                while self.car_thread_is_running and self.car_mode == 6:
                    if self.car.get_mode_clamp() == 2:
                        self.car.mode_clamp()                                     # Set the car mode to clamp
                        print("clamp down...")                                    # Print a message
                    elif self.car.get_mode_clamp() == 0:
                        self.car_mode = self.car_last_mode                        # Update the car mode to the last mode
                        self.tcp_server.sendDataToCmdClinet("CMD_ACTION#20\r\n")  # Send the action command to the client
                        print("clamp down stop")                                  # Print a message
                        break

    def set_threading_video_send(self, state, close_time=0.3):  # Method to start or stop the video sending thread
        if self.video_thread is None:                                                   # Check if the video thread is not initialized
            buf_state = False                                                           # If not, set buffer state to False
        else:
            buf_state = self.video_thread.is_alive()                                    # Otherwise, check if the video thread is running
        if state != buf_state:                                                          # If the desired state is different from the current state
            if state:                                                                   # If the desired state is to start the thread
                self.video_thread_is_running = True                                     # Set the flag indicating the video thread should run
                self.video_thread = threading.Thread(target=self.threading_video_send)  # Create a new video thread
                self.video_thread.start()                                               # Start the video thread
            else:                                                                       # If the desired state is to stop the thread
                self.video_thread_is_running = False                                    # Set the flag indicating the video thread should stop
                if self.video_thread is not None:                                       # If the video thread is initialized
                    self.video_thread.join(close_time)                                  # Wait for the video thread to finish, with a timeout
                    self.video_thread = None                                            # Clear the reference to the video thread

    def threading_video_send(self):                                       # Method that runs in the video sending thread
        while self.video_thread_is_running:                               # Keep running as long as the video thread is active
            if self.tcp_server.isVideoServerConnected():                  # Check if the video server is connected
                self.camera.start_stream()                                # Start the camera stream
                while self.tcp_server.isVideoServerConnected():           # Keep sending frames as long as the video server is connected
                    frame = self.camera.get_frame()                       # Get a frame from the camera
                    lenFrame = len(frame)                                 # Get the length of the frame
                    lengthBin = struct.pack('<I', lenFrame)               # Pack the length into a binary format
                    try:
                        self.tcp_server.sendDataToVideoClient(lengthBin)  # Send the frame length to the video client
                        self.tcp_server.sendDataToVideoClient(frame)      # Send the frame data to the video client
                    except:                                               # If an error occurs during sending
                        break                                             # Break out of the loop
                self.camera.stop_stream()                                 # Stop the camera stream when done

    def set_process_led_running(self, state, close_time=0.3):         # Method to start or stop the LED control process
        if self.led_process is None:                                  # Check if the LED process is not initialized
            buf_state = False                                         # If not, set buffer state to False
        else:
            buf_state = self.led_process.is_alive()                   # Otherwise, check if the LED process is running
        if state != buf_state:                                        # If the desired state is different from the current state
            if state:                                                 # If the desired state is to start the process
                self.led_process_is_running = True                    # Set the flag indicating the LED process should run
                self.led_process = multiprocessing.Process(target=self.process_led_running, args=(self.queue_led,))  # Create a new LED process
                self.led_process.start()                              # Start the LED process
            else:                                                     # If the desired state is to stop the process
                self.led_process_is_running = False                   # Set the flag indicating the LED process should stop
                if self.led_process is not None:                      # If the LED process is initialized
                    try:
                        self.led_process.terminate()                  # Terminate the LED process
                        self.led_process.join(close_time)             # Wait for the LED process to finish, with a timeout
                        self.led_process = None                       # Clear the reference to the LED process
                    except Exception as e:                            # If an error occurs during termination
                        print(f"Error terminating LED process: {e}")  # Print the error message

    def process_led_running(self, queue_led):                      # Method that runs in the LED control process
        led_parameters = [0, 100, 0, 0, 15]                        # Initialize default LED parameters
        try:
            while self.led_process_is_running:                     # Keep running as long as the LED process is active
                if not queue_led.empty():                          # If there are commands in the queue
                    queue_buf_cmd = queue_led.get()                # Get the command from the queue
                    self.led_parser.clearParameters()              # Clear the current parameters
                    self.led_parser.parser(queue_buf_cmd)          # Parse the command
                    led_parameters = self.led_parser.intParameter  # Update the LED parameters
                while queue_led.empty():                           # While there are no commands in the queue
                    if led_parameters[0] == 1:                     # If the command is to control a specific LED
                        self.led.ledIndex(led_parameters[4], led_parameters[1], led_parameters[2], led_parameters[3])  # Control the specified LED
                        time.sleep(0.1)  # Wait for a short period
                    elif led_parameters[0] == 2:                   # If the command is to perform a color wipe
                        self.led.colorWipe((255, 0, 0), 120)       # Red color wipe
                        self.led.colorWipe((0, 255, 0), 120)       # Green color wipe
                        self.led.colorWipe((0, 0, 255), 120)       # Blue color wipe
                        self.led.colorWipe((0, 0, 0), 120)         # Black color wipe
                    elif led_parameters[0] == 3:                   # If the command is to blink LEDs
                        self.led.Blink(led_parameters[1:4], 50)    # Blink with specified colors
                        self.led.Blink((0, 0, 0), 50)              # Turn off LEDs
                    elif led_parameters[0] == 4:                   # If the command is to perform a breathing effect
                        self.led.Breathing(led_parameters[1:4])     # Perform the breathing effect
                    elif led_parameters[0] == 5:                   # If the command is to perform a rainbow cycle
                        self.led.rainbowCycle()                    # Perform the rainbow cycle
                    else:                                          # If the command is unknown or invalid
                        self.led.colorWipe((0, 0, 0), 10)          # Turn off all LEDs
                        break                                      # Exit the loop
        except KeyboardInterrupt:                                  # If a keyboard interrupt is detected
            print("LED process interrupted, cleaning up...")       # Print a cleanup message
            self.led.colorWipe((0, 0, 0), 10)                      # Turn off all LEDs

    def close_application(self):                                # Method to clean up and close the application
        self.ui_button_state = False                            # Set the UI button state to False
        self.set_threading_cmd_receive(False)                   # Stop the command receiving thread
        self.set_threading_video_send(False)                    # Stop the video sending thread
        self.set_threading_car_task(False)                      # Stop the car task thread
        self.set_process_led_running(False)                     # Stop the LED control process
        if self.tcp_server:                                     # If the TCP server is initialized
            self.tcp_server.stopTcpServer()                     # Stop the TCP server
            self.tcp_server = None                              # Clear the reference to the TCP server
        self.stop_car()                                         # Stop the car
        if self.cmd_thread and self.cmd_thread.is_alive():      # If the command thread is running
            self.cmd_thread.join(0.1)                           # Wait for the command thread to finish, with a timeout
        if self.video_thread and self.video_thread.is_alive():  # If the video thread is running
            self.video_thread.join(0.1)                         # Wait for the video thread to finish, with a timeout
        if self.car_thread and self.car_thread.is_alive():      # If the car thread is running
            self.car_thread.join(0.1)                           # Wait for the car thread to finish, with a timeout
        if self.led_process and self.led_process.is_alive():    # If the LED process is running
            self.led_process.terminate()                        # Terminate the LED process
            self.led_process.join(0.1)                          # Wait for the LED process to finish, with a timeout
        self.app.quit()                                         # Quit the application
        sys.exit(1)                                             # Exit the program with status code 1

    def signal_handler(self, signal, frame):             # Signal handler to catch Ctrl+C
        print("Caught Ctrl+C, stopping application...")  # Print a message indicating the application is stopping
        self.close_application()                         # Call the method to close the application

    def check_signals(self):             # Method to check for pending events and exit conditions
        if self.app.hasPendingEvents():  # If there are pending events
            self.app.processEvents()     # Process the pending events
        if not self.ui_button_state and not self.cmd_thread_is_running and not self.video_thread_is_running and not self.led_process_is_running and not self.action_process_is_running:  # If all threads and processes are stopped
            self.app.quit()              # Quit the application

if __name__ == '__main__':        # Entry point of the script
    myshow = mywindow()           # Create an instance of the main window
    myshow.show()                 # Show the main window
    sys.exit(myshow.app.exec_())  # Run the application and exit with the appropriate status code