def test_Parameter():
    from parameter import ParameterManager               # Import the ParameterManager class from the parameter module
    manager = ParameterManager()                         # Initialize the ParameterManager instance
    if manager.file_exists("params.json") and manager.validate_params("params.json"):  # Check if the params.json file exists and is valid
        pcb_version = manager.get_pcb_version()          # Get the PCB version
        print(f"PCB Version: {pcb_version}.0")           # Print the PCB version
        pi_version = manager.get_raspberry_pi_version()  # Get the Raspberry Pi version
        print(f"Raspberry PI version is {'less than 5' if pi_version == 1 else '5'}.")  # Print the Raspberry Pi version

def test_Led():
    from led import Led                        # Import the Led class from the led module
    import time                                # Import the time module for sleep functionality
    print('Program is starting ... ')          # Print a start message
    led = Led()                                # Initialize the Led instance
    try:
        while True:
            print("ledIndex test")             # Print a test message
            led.ledIndex(0x01, 255, 0, 0)      # Set LED 1 to red
            led.ledIndex(0x02, 0, 255, 0)      # Set LED 2 to green
            led.ledIndex(0x04, 0, 0, 255)      # Set LED 3 to blue
            led.ledIndex(0x08, 255, 255, 255)  # Set LED 4 to white
            time.sleep(3)                      # Wait for 3 seconds

            print("colorWipe test")            # Print a test message
            led.colorWipe((255, 0, 0))         # Perform a red color wipe
            led.colorWipe((0, 255, 0))         # Perform a green color wipe
            led.colorWipe((0, 0, 255))         # Perform a blue color wipe
            time.sleep(1)                      # Wait for 1 second

            print("theaterChaseRainbow test")  # Print a test message
            led.theaterChaseRainbow()          # Perform a theater chase rainbow effect
            print("rainbow test")              # Print a test message
            led.rainbow()                      # Perform a rainbow effect
            print("rainbowCycle test")         # Print a test message
            led.rainbowCycle()                 # Perform a rainbow cycle effect

            led.colorWipe((0, 0, 0), 10)       # Turn off all LEDs
    except KeyboardInterrupt:                  # Handle keyboard interrupt (Ctrl+C)
        led.colorWipe((0, 0, 0), 10)           # Turn off all LEDs
        print("\nEnd of program")              # Print an end message

def test_Motor():
    from motor import tankMotor              # Import the tankMotor class from the motor module
    import time                              # Import the time module for sleep functionality
    print('Program is starting ... ')        # Print a start message
    PWM = tankMotor()                        # Initialize the tankMotor instance
    try:
        PWM.setMotorModel(2000, 2000)        # Move the car forward
        print("The car is moving forward")   # Print a status message
        time.sleep(1)                        # Wait for 1 second
        PWM.setMotorModel(-2000, -2000)      # Move the car backward
        print("The car is going backwards")  # Print a status message
        time.sleep(1)                        # Wait for 1 second
        PWM.setMotorModel(-2000, 2000)       # Turn the car left
        print("The car is turning left")     # Print a status message
        time.sleep(1)                        # Wait for 1 second
        PWM.setMotorModel(2000, -2000)       # Turn the car right
        print("The car is turning right")    # Print a status message
        time.sleep(1)                        # Wait for 1 second
        PWM.setMotorModel(0, 0)              # Stop the car
        print("\nEnd of program")            # Print an end message
    except KeyboardInterrupt:                # Handle keyboard interrupt (Ctrl+C)
        PWM.setMotorModel(0, 0)              # Stop the car
        print("\nEnd of program")            # Print an end message

def test_Ultrasonic():
    from ultrasonic import Ultrasonic                              # Import the Ultrasonic class from the ultrasonic module
    import time                                                    # Import the time module for sleep functionality
    print('Program is starting ... ')                              # Print a start message
    ultrasonic = Ultrasonic()                                      # Initialize the Ultrasonic instance
    try:
        while True:
            distance = ultrasonic.get_distance()                   # Get the distance to the obstacle
            print("Obstacle distance is " + str(distance) + "CM")  # Print the distance
            time.sleep(0.3)                                        # Wait for 0.3 seconds
    except KeyboardInterrupt:                                      # Handle keyboard interrupt (Ctrl+C)
        print("\nEnd of program")                                  # Print an end message

def test_Infrared():
    from infrared import Infrared      # Import the Infrared class from the infrared module
    import time                        # Import the time module for sleep functionality
    print('Program is starting ... ')  # Print a start message
    infrared = Infrared()              # Initialize the Infrared instance
    try:
        while True:
            if infrared.read_one_infrared(1) == 0 and infrared.read_one_infrared(2) == 1 and infrared.read_one_infrared(3) == 0:
                print('Middle')        # Print a middle detection message
            elif infrared.read_one_infrared(1) == 1 and infrared.read_one_infrared(2) == 0 and infrared.read_one_infrared(3) == 1:
                print('Middle')        # Print a middle detection message
            elif infrared.read_one_infrared(1) == 0 and infrared.read_one_infrared(2) == 0 and infrared.read_one_infrared(3) == 1:
                print('Right')         # Print a right detection message
            elif infrared.read_one_infrared(1) == 1 and infrared.read_one_infrared(2) == 1 and infrared.read_one_infrared(3) == 0:
                print('Right')         # Print a right detection message
            elif infrared.read_one_infrared(1) == 1 and infrared.read_one_infrared(2) == 0 and infrared.read_one_infrared(3) == 0:
                print('Left')          # Print a left detection message
            elif infrared.read_one_infrared(1) == 0 and infrared.read_one_infrared(2) == 1 and infrared.read_one_infrared(3) == 1:
                print('Left')          # Print a left detection message
            time.sleep(0.1)            # Wait for 0.1 seconds
    except KeyboardInterrupt:          # Handle keyboard interrupt (Ctrl+C)
        print("\nEnd of program")      # Print an end message

def test_Servo():
    from servo import Servo            # Import the Servo class from the servo module
    import time                        # Import the time module for sleep functionality
    print('Program is starting ... ')  # Print a start message
    servo = Servo()                    # Initialize the Servo instance
    try:
        while True:
            for i in range(90, 150, 1):
                servo.setServoAngle('0', i)  # Set servo 0 to angle i
                time.sleep(0.01)           # Wait for 0.01 seconds
            for i in range(140, 90, -1):
                servo.setServoAngle('1', i)  # Set servo 1 to angle i
                time.sleep(0.01)           # Wait for 0.01 seconds
            for i in range(90, 140, 1):
                servo.setServoAngle('1', i)  # Set servo 1 to angle i
                time.sleep(0.01)           # Wait for 0.01 seconds
            for i in range(150, 90, -1):
                servo.setServoAngle('0', i)  # Set servo 0 to angle i
                time.sleep(0.01)           # Wait for 0.01 seconds
    except KeyboardInterrupt:              # Handle keyboard interrupt (Ctrl+C)
        servo.setServoAngle('0', 90)         # Set servo 0 to 90 degrees
        servo.setServoAngle('1', 140)        # Set servo 1 to 140 degrees
        print("\nEnd of program")          # Print an end message

def test_Camera():
    import time
    from camera import Camera         # Import the Camera class from the camera module
    print("test camera")              # Print a test message
    camera = Camera()                 # Initialize the Camera instance
    camera.start_image()              # Start the camera
    print("Take a photo and save it as 'image.jpg' after 5 seconds.")
    time.sleep(5)   
    camera.save_image("image.jpg")  # Capture an image and save it as test.jpg
    camera.close()                    # Close the camera
    print("Camera test finished")     # Print a finish message

# Main program logic follows:
if __name__ == '__main__':
    import sys  # Import the sys module for command-line arguments
    if len(sys.argv) < 2:
        print("Parameter error: Please assign the device")       # Print an error message if no device is specified
        exit()                                                   # Exit the program
    if sys.argv[1] == 'Parameter' or sys.argv[1] == 'parameter':
        test_Parameter()                                         # Run the parameter test
    elif sys.argv[1] == 'Led' or sys.argv[1] == 'led':
        test_Led()                                               # Run the LED test
    elif sys.argv[1] == 'Motor' or sys.argv[1] == 'motor':
        test_Motor()                                             # Run the motor test
    elif sys.argv[1] == 'Ultrasonic' or sys.argv[1] == 'ultrasonic':
        test_Ultrasonic()                                        # Run the ultrasonic test
    elif sys.argv[1] == 'Infrared' or sys.argv[1] == 'infrared':
        test_Infrared()                                          # Run the infrared test
    elif sys.argv[1] == 'Servo' or sys.argv[1] == 'servo':
        test_Servo()                                             # Run the servo test
    elif sys.argv[1] == 'Camera' or sys.argv[1] == 'camera':
        test_Camera()                                            # Run the camera test