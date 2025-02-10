# Import the Motor class from the gpiozero library
from gpiozero import Motor

# Define the tankMotor class to control the motors of a tank-like robot
class tankMotor:
    def __init__(self):
        """Initialize the tankMotor class with GPIO pins for the left and right motors."""
        self.left_motor = Motor(23, 24)  # Initialize the left motor with GPIO pins 23 and 24
        self.right_motor = Motor(6, 5)   # Initialize the right motor with GPIO pins 6 and 5

    def duty_range(self, duty1, duty2):
        """Ensure the duty cycle values are within the valid range (-4095 to 4095)."""
        if duty1 > 4095:
            duty1 = 4095     # Cap the value at 4095 if it exceeds the maximum
        elif duty1 < -4095:
            duty1 = -4095    # Cap the value at -4095 if it falls below the minimum
        
        if duty2 > 4095:
            duty2 = 4095     # Cap the value at 4095 if it exceeds the maximum
        elif duty2 < -4095:
            duty2 = -4095    # Cap the value at -4095 if it falls below the minimum
        
        return duty1, duty2  # Return the clamped duty cycle values

    def left_Wheel(self, duty):
        """Control the left wheel based on the duty cycle value."""
        if duty > 0:
            self.left_motor.forward(duty / 4096)    # Move the left motor forward
        elif duty < 0:
            self.left_motor.backward(-duty / 4096)  # Move the left motor backward
        else:
            self.left_motor.stop()                  # Stop the left motor

    def right_Wheel(self, duty):
        """Control the right wheel based on the duty cycle value."""
        if duty > 0:
            self.right_motor.forward(duty / 4096)    # Move the right motor forward
        elif duty < 0:
            self.right_motor.backward(-duty / 4096)  # Move the right motor backward
        else:
            self.right_motor.stop()                  # Stop the right motor

    def setMotorModel(self, duty1, duty2):
        """Set the duty cycle for both motors and ensure they are within the valid range."""
        duty1, duty2 = self.duty_range(duty1, duty2)  # Clamp the duty cycle values
        self.left_Wheel(duty1)   # Control the left wheel
        self.right_Wheel(duty2)  # Control the right wheel
    
    def close(self):
        """Close the motors to release resources."""
        self.left_motor.close()   # Close the left motor
        self.right_motor.close()  # Close the right motor

# Main program logic follows:
if __name__ == '__main__':
    import time  # Import the time module for sleep functionality
    print('Program is starting ... \n')  # Print a start message
    pwm_motor = tankMotor()              # Create an instance of the tankMotor class

    try:
        pwm_motor.setMotorModel(2000, 2000)    # Set both motors to move forward
        time.sleep(1)                          # Wait for 1 second
        pwm_motor.setMotorModel(-2000, -2000)  # Set both motors to move backward
        time.sleep(1)                          # Wait for 1 second
        pwm_motor.setMotorModel(2000, -2000)   # Turn right(left motor forward, right motor backward)
        time.sleep(1)                          # Wait for 1 second
        pwm_motor.setMotorModel(-2000, 2000)   # Turn left(left motor backward, right motor forward)
        time.sleep(1)                          # Wait for 1 second
        pwm_motor.setMotorModel(0, 0)          # Stop both motors
        time.sleep(1)                          # Wait for 1 second
    except KeyboardInterrupt:                  # Handle a keyboard interrupt (Ctrl+C)
        pwm_motor.setMotorModel(0, 0)          # Stop both motors
        pwm_motor.close()                      # Close the motors to release resources