# Import necessary modules for ultrasonic sensor, motor control, servo control, and infrared sensor
from ultrasonic import Ultrasonic
from motor import tankMotor
from servo import Servo
from infrared import Infrared
import time

# Define the Car class to manage all components and functionalities
class Car:
    def __init__(self):
        # Initialize all components to None
        self.servo = None
        self.sonic = None
        self.motor = None
        self.infrared = None
        # Call the start method to initialize components
        self.start()

    def start(self):   
        # Set initial clamp mode and infrared run stop flag
        self.clamp_mode = 0
        self.infrared_run_stop = False
        # Initialize servo if not already initialized
        if self.servo is None:
            self.servo = Servo()
        # Initialize ultrasonic sensor if not already initialized
        if self.sonic is None:
            self.sonic = Ultrasonic()
        # Initialize motor if not already initialized
        if self.motor is None:
            self.motor = tankMotor()
        # Initialize infrared sensor if not already initialized
        if self.infrared is None:
            self.infrared = Infrared()

    def close(self):
        # Reset clamp mode
        self.clamp_mode = 0
        # Stop servo
        self.servo.setServoStop()
        # Close ultrasonic sensor
        self.sonic.close()
        # Close motor
        self.motor.close()
        # Close infrared sensor
        self.infrared.close()
        # Set all components to None
        self.servo = None
        self.sonic = None
        self.motor = None
        self.infrared = None

    def mode_ultrasonic(self):
        # Get distance from ultrasonic sensor
        distance = self.sonic.get_distance()
        # print("Ultrasonic distance is " + str(distance) + "CM")

        # Check if distance is valid
        if distance != 0:
            # If distance is less than 45 cm, move backward and turn left
            if distance < 45:
                self.motor.setMotorModel(-1500, -1500)
                time.sleep(0.4)
                self.motor.setMotorModel(-1500, 1500)
                time.sleep(0.2)
            # Otherwise, move forward
            else:
                self.motor.setMotorModel(1500, 1500)
        # Sleep for a short duration
        time.sleep(0.2)
    
    def mode_infrared(self):
        # Get distance from ultrasonic sensor
        distance = self.sonic.get_distance()
        # Read all infrared sensors
        infrared_value = self.infrared.read_all_infrared()
        # print("distance:", distance, "infrared:", infrared_value)

        # Control motor based on infrared sensor values
        if infrared_value == 2:
            self.motor.setMotorModel(1200, 1200)    # Move forward
        elif infrared_value == 4:
            self.motor.setMotorModel(-1500, 2500)   # Turn left
        elif infrared_value == 6:
            self.motor.setMotorModel(-2000, 4000)   # Turn left more sharply
        elif infrared_value == 1:
            self.motor.setMotorModel(2500, -1500)   # Turn right
        elif infrared_value == 3:
            self.motor.setMotorModel(4000, -2000)   # Turn right more sharply
        elif infrared_value == 7:
            self.motor.setMotorModel(0, 0)          # Stop

        # If distance is between 5.0 and 12.0 cm, perform clamp operations
        if distance > 5.0 and distance <= 12.0:
            self.motor.setMotorModel(0, 0)          # Stop motor
            self.set_mode_clamp(1)                  # Set clamp mode to 1 (up)
            while self.get_mode_clamp() == 1 and self.infrared_run_stop == False:
                self.mode_clamp()                   # Perform clamp up operation
            if self.infrared_run_stop == True:
                self.motor.setMotorModel(0, 0)      # Stop motor if infrared run stop is True
                return
            self.motor.setMotorModel(-1500, 1500)   # Turn left
            time.sleep(1.5)
            self.motor.setMotorModel(0, 0)          # Stop motor
            self.set_mode_clamp(2)                  # Set clamp mode to 2 (down)
            while self.get_mode_clamp() == 2 and self.infrared_run_stop == False:
                self.mode_clamp()                   # Perform clamp down operation
            if self.infrared_run_stop == True:
                self.motor.setMotorModel(0, 0)      # Stop motor if infrared run stop is True
                return 
            self.motor.setMotorModel(1500, -1500)   # Turn right
            time.sleep(1.4)

    def mode_clamp_up(self):
        # Perform clamp up operation if clamp mode is 1
        if self.clamp_mode == 1:
            # Get distance from ultrasonic sensor
            distance = self.sonic.get_distance()
            # Print the distance
            print("car_mode_clamp_up distance:", distance)
            # Control motor based on distance
            if distance <= 5:
                self.motor.setMotorModel(-1200, -1200)  # Move backward slowly
            elif distance > 5 and distance < 7.5:
                self.motor.setMotorModel(-800, -800)    # Move backward faster
            elif distance >= 7.5 and distance <= 7.7:
                self.motor.setMotorModel(0, 0)          # Stop motor
                # Adjust servos to clamp up
                for i in range(140, 90, -1):
                    self.servo.setServoAngle('1', i)
                    time.sleep(0.01)
                for i in range(90, 130, 1):
                    self.servo.setServoAngle('0', i)
                    time.sleep(0.01)  
                for i in range(90, 140, 1):
                    self.servo.setServoAngle('1', i)
                    time.sleep(0.01)
                self.clamp_mode = 0                     # Reset clamp mode
            elif distance > 7.7 and distance < 11:
                self.motor.setMotorModel(800, 800)      # Move forward slowly
            elif distance >= 11:
                self.motor.setMotorModel(1200, 1200)    # Move forward quickly
            # Sleep for a short duration
            time.sleep(0.05) 

    def mode_clamp_down(self):
        # Perform clamp down operation if clamp mode is 2
        if self.clamp_mode == 2:
            self.motor.setMotorModel(0, 0)              # Stop motor
            # Adjust servos to clamp down
            for i in range(140, 90, -1):
                self.servo.setServoAngle('1', i)
                time.sleep(0.01)
            for i in range(130, 90, -1):
                self.servo.setServoAngle('0', i)
                time.sleep(0.01)
            for i in range(90, 140, 1):
                self.servo.setServoAngle('1', i)
                time.sleep(0.01)
            self.clamp_mode = 0                         # Reset clamp mode

    def mode_clamp_stop(self):
        # Stop motor
        self.motor.setMotorModel(0, 0)

    def set_mode_clamp(self, mode=0):  
        # Set clamp mode
        self.clamp_mode = mode 

    def get_mode_clamp(self):
        # Get current clamp mode
        return self.clamp_mode

    def mode_clamp(self, mode=None):
        # Set clamp mode if provided
        if mode is not None:
            self.clamp_mode = mode
        # Perform clamp operation based on current mode
        if self.clamp_mode == 1:
            self.mode_clamp_up()
        elif self.clamp_mode == 2:
            self.mode_clamp_down()
        elif self.clamp_mode == 0:
            self.mode_clamp_stop()

# Test function for clamp functionality
def test_car_clamp():
    car = Car()  # Create a Car object
    try:
        while True:
            print("clamp up...")
            car.clamp_mode = 1  # Set clamp mode to 1 (up)
            while car.clamp_mode == 1:
                car.mode_clamp()  # Perform clamp up operation
            time.sleep(1)

            print("clamp down...")
            car.clamp_mode = 2  # Set clamp mode to 2 (down)
            while car.clamp_mode == 2:
                car.mode_clamp()  # Perform clamp down operation
            time.sleep(1)

            print("clamp stop...")
            car.mode_clamp(0)  # Stop clamp operation
            time.sleep(1)

    except KeyboardInterrupt:
        car.close()  # Close the car object
        print("\nEnd of program")

# Test function for infrared sensor functionality
def test_car_infrared():
    car = Car()  # Create a Car object
    try:
        while True:
            car.mode_infrared()  # Perform infrared sensor operation
    except KeyboardInterrupt:
        car.close()  # Close the car object
        print("\nEnd of program")

# Test function for ultrasonic sensor functionality
def test_car_sonic():
    car = Car()  # Create a Car object
    try:
        while True:
            car.mode_ultrasonic()  # Perform ultrasonic sensor operation
    except KeyboardInterrupt:
        car.close()  # Close the car object
        print("\nEnd of program")

# Main entry point of the program
if __name__ == '__main__':
    # Uncomment the following lines to test different functionalities
    # test_car_clamp()  # Test clamp functionality
    # test_car_infrared()  # Test infrared sensor functionality
    # test_car_sonic()  # Test ultrasonic sensor functionality
    import sys  # Import the sys module for command-line arguments
    if len(sys.argv) < 2:
        print("Parameter error: Please assign the device")       # Print an error message if no device is specified
        exit()                                                   # Exit the program
    if sys.argv[1] == 'Sonic' or sys.argv[1] == 'sonnic':
        test_car_sonic()                                        # Run the ultrasonic test
    elif sys.argv[1] == 'Infrared' or sys.argv[1] == 'infrared':
        test_car_infrared()                                          # Run the infrared test
 