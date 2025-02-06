import pigpio
class PigpioServo:
    def __init__(self):
        # Initialize the PigpioServo instance
        self.channel1 = 7  # GPIO pin for channel 1
        self.channel2 = 8  # GPIO pin for channel 2
        self.channel3 = 25  # GPIO pin for channel 3
        self.PwmServo = pigpio.pi()  # Initialize the pigpio library
        self.PwmServo.set_mode(self.channel1, pigpio.OUTPUT)  # Set channel 1 as output
        self.PwmServo.set_mode(self.channel2, pigpio.OUTPUT)  # Set channel 2 as output
        self.PwmServo.set_mode(self.channel3, pigpio.OUTPUT)  # Set channel 3 as output
        self.PwmServo.set_PWM_frequency(self.channel1, 50)  # Set PWM frequency for channel 1 to 50 Hz
        self.PwmServo.set_PWM_frequency(self.channel2, 50)  # Set PWM frequency for channel 2 to 50 Hz
        self.PwmServo.set_PWM_frequency(self.channel3, 50)  # Set PWM frequency for channel 3 to 50 Hz
        self.PwmServo.set_PWM_range(self.channel1, 4000)  # Set PWM range for channel 1 to 4000
        self.PwmServo.set_PWM_range(self.channel2, 4000)  # Set PWM range for channel 2 to 4000
        self.PwmServo.set_PWM_range(self.channel3, 4000)  # Set PWM range for channel 3 to 4000

    def setServoPwm(self, channel, angle):
        # Set the PWM duty cycle for the specified channel and angle
        if channel == '0':
            self.PwmServo.set_PWM_dutycycle(self.channel1, 80 + (400 / 180) * angle)  # Calculate and set PWM duty cycle for channel 1
        elif channel == '1':
            self.PwmServo.set_PWM_dutycycle(self.channel2, 80 + (400 / 180) * angle)  # Calculate and set PWM duty cycle for channel 2
        elif channel == '2':
            self.PwmServo.set_PWM_dutycycle(self.channel3, 80 + (400 / 180) * angle)  # Calculate and set PWM duty cycle for channel 3

from gpiozero import AngularServo
class GpiozeroServo:
    def __init__(self):
        # Initialize the GpiozeroServo instance
        self.channel1 = 7  # GPIO pin for channel 1
        self.channel2 = 8  # GPIO pin for channel 2
        self.channel3 = 25  # GPIO pin for channel 3
        self.myCorrection = 0.0  # Correction value for pulse width
        self.maxPW = (2.5 + self.myCorrection) / 1000  # Maximum pulse width
        self.minPW = (0.5 - self.myCorrection) / 1000  # Minimum pulse width
        self.servo1 = AngularServo(self.channel1, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=self.minPW, max_pulse_width=self.maxPW)  # Initialize servo 1
        self.servo2 = AngularServo(self.channel2, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=self.minPW, max_pulse_width=self.maxPW)  # Initialize servo 2
        self.servo3 = AngularServo(self.channel3, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=self.minPW, max_pulse_width=self.maxPW)  # Initialize servo 3

    def setServoPwm(self, channel, angle):
        # Set the angle for the specified channel
        if channel == '0':
            self.servo1.angle = angle  # Set angle for servo 1
        elif channel == '1':
            self.servo2.angle = angle  # Set angle for servo 2
        elif channel == '2':
            self.servo3.angle = angle  # Set angle for servo 3

from rpi_hardware_pwm import HardwarePWM
class HardwareServo:
    def __init__(self, pcb_version):
        # Initialize the HardwareServo instance
        self.pcb_version = pcb_version  # PCB version
        self.pwm_gpio12 = None  # PWM object for GPIO 12
        self.pwm_gpio13 = None  # PWM object for GPIO 13
        if self.pcb_version == 1:
            self.pwm_gpio12 = HardwarePWM(pwm_channel=0, hz=50, chip=0)  # Initialize PWM for GPIO 12 on chip 0
            self.pwm_gpio13 = HardwarePWM(pwm_channel=1, hz=50, chip=0)  # Initialize PWM for GPIO 13 on chip 0
        elif self.pcb_version == 2:
            self.pwm_gpio12 = HardwarePWM(pwm_channel=0, hz=50, chip=2)  # Initialize PWM for GPIO 12 on chip 2
            self.pwm_gpio13 = HardwarePWM(pwm_channel=1, hz=50, chip=2)  # Initialize PWM for GPIO 13 on chip 2
        self.pwm_gpio12.start(0)  # Start PWM for GPIO 12 with 0% duty cycle
        self.pwm_gpio13.start(0)  # Start PWM for GPIO 13 with 0% duty cycle

    def setServoStop(self, channel):
        # Stop the PWM for the specified channel
        if channel == '0':
            self.pwm_gpio12.stop()  # Stop PWM for GPIO 12
        elif channel == '1':
            self.pwm_gpio13.stop()  # Stop PWM for GPIO 13

    def setServoFrequency(self, channel, freq):
        # Set the PWM frequency for the specified channel
        if channel == '0':
            self.pwm_gpio12.change_frequency(freq)  # Change frequency for GPIO 12
        elif channel == '1':
            self.pwm_gpio13.change_frequency(freq)  # Change frequency for GPIO 13

    def setServoDuty(self, channel, duty):
        # Set the PWM duty cycle for the specified channel
        if channel == '0':
            self.pwm_gpio12.change_duty_cycle(duty)  # Change duty cycle for GPIO 12
        elif channel == '1':
            self.pwm_gpio13.change_duty_cycle(duty)  # Change duty cycle for GPIO 13

    def map(self, x, in_min, in_max, out_min, out_max):
        # Map a value from one range to another
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def setServoPwm(self, channel, angle):
        # Set the PWM duty cycle for the specified channel and angle
        if channel == '0':
            duty = self.map(angle, 0, 180, 2.5, 12.5)  # Map angle to duty cycle
            self.setServoDuty(channel, duty)  # Set duty cycle for GPIO 12
        elif channel == '1':
            duty = self.map(angle, 0, 180, 2.5, 12.5)  # Map angle to duty cycle
            self.setServoDuty(channel, duty)  # Set duty cycle for GPIO 13

from parameter import ParameterManager
class Servo:
    def __init__(self):
        # Initialize the Servo instance
        self.param = ParameterManager()  # Initialize parameter manager
        self.pcb_version = self.param.get_pcb_version()  # Get PCB version
        self.pi_version = self.param.get_raspberry_pi_version()  # Get Raspberry Pi version

        if self.pcb_version == 1 and self.pi_version == 1:
            self.pwm = PigpioServo()  # Use PigpioServo for PCB version 1 and Raspberry Pi version 1
        elif self.pcb_version == 1 and self.pi_version == 2:
            self.pwm = GpiozeroServo()  # Use GpiozeroServo for PCB version 1 and Raspberry Pi version 2
        elif self.pcb_version == 2 and self.pi_version == 1:
            self.pwm = HardwareServo(1)  # Use HardwareServo for PCB version 2 and Raspberry Pi version 1
        elif self.pcb_version == 2 and self.pi_version == 2:
            self.pwm = HardwareServo(2)  # Use HardwareServo for PCB version 2 and Raspberry Pi version 2
        self.pwm.setServoPwm("0", 90)  # Set initial angle for servo 0
        self.pwm.setServoPwm("1", 140)  # Set initial angle for servo 1

    def angle_range(self, channel, init_angle):
        # Ensure the angle is within the valid range for the specified channel
        if channel == '0':
            if init_angle < 90:
                init_angle = 90  # Minimum angle for channel 0
            elif init_angle > 150:
                init_angle = 150  # Maximum angle for channel 0
        elif channel == '1':
            if init_angle < 90:
                init_angle = 90  # Minimum angle for channel 1
            elif init_angle > 150:
                init_angle = 150  # Maximum angle for channel 1
        elif channel == '2':
            if init_angle < 0:
                init_angle = 0  # Minimum angle for channel 2
            elif init_angle > 180:
                init_angle = 180  # Maximum angle for channel 2
        return init_angle

    def setServoAngle(self, channel, angle):
        # Set the angle for the specified channel
        angle = self.angle_range(str(channel), int(angle))  # Ensure the angle is within the valid range
        self.pwm.setServoPwm(str(channel), int(angle))  # Set the angle for the specified channel

    def setServoStop(self):
        # Stop the PWM for all servos
        if self.pcb_version == 2:
            self.pwm.setServoStop('0')  # Stop PWM for servo 0
            self.pwm.setServoStop('1')  # Stop PWM for servo 1

# Main program logic follows:
if __name__ == '__main__':
    import time
    servo = Servo()  # Create an instance of the Servo class

    print("Now servo 0 will be rotated to 150° and servos 1 will be rotated to 90°.")
    print("If they were already at 150° and 90°, nothing would be observed.")
    print("Please keep the program running when installing the servos.")
    print("After that, you can press ctrl-C to end the program.")

    try:
        while True:
            servo.setServoAngle('0', 150)  # Set the angle for servo 0 to 150°
            servo.setServoAngle('1', 90)   # Set the angle for servo 1 to 90°
            time.sleep(1)  # Wait for 1 second before repeating the loop
    except KeyboardInterrupt:
        # Gradually decrease the angle of servo 0 from 150° to 90°
        for i in range(150, 90, -1):
            servo.setServoAngle('0', i)
            time.sleep(0.01)  # Wait for 0.01 seconds between each step

        # Gradually increase the angle of servo 1 from 90° to 140°
        for i in range(90, 140, 1):
            servo.setServoAngle('1', i)
            time.sleep(0.01)  # Wait for 0.01 seconds between each step

        servo.setServoStop()  # Stop the servos
        print("\nEnd of program")  # Print a message indicating the end of the program
