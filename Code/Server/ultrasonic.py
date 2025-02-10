from gpiozero import DistanceSensor, PWMSoftwareFallback
import warnings

class Ultrasonic:
    def __init__(self):
        # Initialize the Ultrasonic class and set up the distance sensor.
        warnings.filterwarnings("ignore", category=PWMSoftwareFallback)  # Ignore PWM software fallback warnings
        self.trigger_pin = 27  # Set the trigger pin number
        self.echo_pin = 22     # Set the echo pin number
        self.sensor = DistanceSensor(echo=self.echo_pin, trigger=self.trigger_pin, max_distance=3)  # Initialize the distance sensor

    def get_distance(self):
        # Get the distance measurement from the ultrasonic sensor in centimeters.
        distance_cm = self.sensor.distance * 100  # Convert distance from meters to centimeters
        return round(float(distance_cm), 1)       # Return the distance rounded to one decimal place

    def close(self):
        # Close the distance sensor.
        self.sensor.close()        # Close the sensor to release resources

if __name__ == '__main__':
    import time  # Import the time module for sleep functionality
    ultrasonic = Ultrasonic()      # Initialize the Ultrasonic instance
    try:
        while True:
            print("Ultrasonic distance: {}cm".format(ultrasonic.get_distance()))  # Print the distance measurement
            time.sleep(0.5)        # Wait for 0.5 seconds
    except KeyboardInterrupt:      # Handle keyboard interrupt (Ctrl+C)
        ultrasonic.close()         # Close the sensor
        print("\nEnd of program")  # Print an end message