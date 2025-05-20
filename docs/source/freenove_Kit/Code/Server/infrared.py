# Import the ParameterManager class for managing configuration parameters
from parameter import ParameterManager
# Import the LineSensor class from gpiozero for reading infrared sensors
from gpiozero import LineSensor

# Define the Infrared class to manage infrared sensors
class Infrared:
    def __init__(self):
        # Initialize the ParameterManager instance
        self.param = ParameterManager()
        # Get the PCB version from the parameter file
        self.pcb_version = self.param.get_pcb_version()
        # Get the Raspberry Pi version from the parameter file
        self.pi_version = self.param.get_raspberry_pi_version()

        # Set GPIO pins based on the PCB version
        if self.pcb_version == 1:
            self.IR01 = 16
            self.IR02 = 20
            self.IR03 = 21
        elif self.pcb_version == 2:
            self.IR01 = 16
            self.IR02 = 26
            self.IR03 = 21

        # Print the GPIO pin numbers for debugging (commented out)
        # print(self.IR01, self.IR02, self.IR03)
        # Initialize LineSensor objects for each infrared sensor
        self.IR01_sensor = LineSensor(self.IR01)
        self.IR02_sensor = LineSensor(self.IR02)
        self.IR03_sensor = LineSensor(self.IR03)

    def read_one_infrared(self, channel):
        # Return 1 if the sensor value is True, otherwise return 0
        if channel == 1:
            return 1 if self.IR01_sensor.value else 0
        elif channel == 2:
            return 1 if self.IR02_sensor.value else 0
        elif channel == 3:
            return 1 if self.IR03_sensor.value else 0

    def read_all_infrared(self):
        # Combine the values of all three sensors into a single integer
        return (self.read_one_infrared(1) << 2) | (self.read_one_infrared(2) << 1) | self.read_one_infrared(3)

    def close(self):
        # Close each LineSensor object to release GPIO resources
        self.IR01_sensor.close()
        self.IR02_sensor.close()
        self.IR03_sensor.close()

# Main entry point for testing the Infrared class
if __name__ == '__main__':
    import time
    # Create an Infrared object
    infrared = Infrared()
    try:
        # Continuously read and print the combined value of all infrared sensors
        while True:
            infrared_value = infrared.read_all_infrared()
            print("Infrared value: {}".format(infrared_value))
            time.sleep(0.5)
    except KeyboardInterrupt:
        # Close the Infrared object and print a message when interrupted
        infrared.close()
        print("\nEnd of program")