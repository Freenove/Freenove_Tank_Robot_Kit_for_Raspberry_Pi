# Import necessary modules
import time
from parameter import ParameterManager
from rpi_ledpixel import Freenove_RPI_WS281X
from spi_ledpixel import Freenove_SPI_LedPixel

# Define the Led class to manage LED strip functionality
class Led:
    def __init__(self):
        """Initialize the Led class and set up LED strip based on PCB and Raspberry Pi versions."""
        # Initialize the ParameterManager instance
        self.param = ParameterManager()
        # Get the PCB version from the parameter file
        self.pcb_version = self.param.get_pcb_version()
        # Get the Raspberry Pi version from the parameter file
        self.pi_version = self.param.get_raspberry_pi_version()
        
        # Set up the LED strip based on PCB and Raspberry Pi versions
        if self.pcb_version == 1 and self.pi_version == 1:
            self.strip = Freenove_RPI_WS281X(4, 255, 'RGB')
            self.is_support_led_function = True

        elif self.pcb_version == 2 and (self.pi_version == 1 or self.pi_version == 2):
            self.strip = Freenove_SPI_LedPixel(4, 255, 'GRB')
            self.is_support_led_function = True

        elif self.pcb_version == 1 and self.pi_version == 2:
            # Print an error message and disable LED function if unsupported combination
            print("PCB Version 1.0 is not supported on Raspberry PI 5.")
            self.is_support_led_function = False

        # Initialize LED strip properties if supported
        if self.is_support_led_function == True:
            self.LedMod = '1'
            self.recv_color = [20, 0, 0]
            self.led_count = 4
            self.start = time.time()
            self.next = 0
            self.ws2812_breathe_flag = 0
            self.breathe_brightness = 0
            self.iteration = 0
            self.color_wheel_value = 0

    def colorWipe(self, change_color, wait_ms=50):
        """Wipe color across display a pixel at a time."""
        if self.is_support_led_function == False:
            return
        else:
            # Iterate through each LED and set its color
            for i in range(self.strip.get_led_count()):
                self.strip.set_led_rgb_data(i, change_color)
                self.strip.show()
                time.sleep(wait_ms / 1000.0)

    def Blink(self, color, wait_ms=50):
        """Blink all LEDs with the specified color."""
        if self.is_support_led_function == False:
            return
        else:
            # Set all LEDs to the specified color and show
            for i in range(self.strip.get_led_count()):
                self.strip.set_led_rgb_data(i, color)
                self.strip.show()
            time.sleep(wait_ms / 1000.0)

    def wheel(self, pos):
        """Generate rainbow colors across 0-255 positions."""
        if self.is_support_led_function == False:
            return
        else:
            if pos < 0 or pos > 255:
                r = g = b = 0
            elif pos < 85:
                r = pos * 3
                g = 255 - pos * 3
                b = 0
            elif pos < 170:
                pos -= 85
                r = 255 - pos * 3
                g = 0
                b = pos * 3
            else:
                pos -= 170
                r = 0
                g = pos * 3
                b = 255 - pos * 3
            return (r, g, b)

    def rainbow(self, wait_ms=20, iterations=1):
        """Draw rainbow that fades across all pixels at once."""
        if self.is_support_led_function == False:
            return
        else:
            # Generate and display rainbow colors
            for j in range(256 * iterations):
                for i in range(self.strip.get_led_count()):
                    self.strip.set_led_rgb_data(i, self.wheel((i + j) & 255))
                self.strip.show()
                time.sleep(wait_ms / 1000.0)

    def Breathing(self, data, wait_ms=5):
        """Breathing effect for the LED strip."""
        if self.is_support_led_function == False:
            return
        else:
            self.next = time.time()
            if (self.next - self.start > (wait_ms / 1000.0)) and (self.ws2812_breathe_flag == 0):
                self.start = self.next
                self.breathe_brightness = self.breathe_brightness + 1
                for i in range(self.strip.get_led_count()):
                    self.strip.set_led_rgb_data(i, (int(data[0] * self.breathe_brightness / 255), int(data[1] * self.breathe_brightness / 255), int(data[2] * self.breathe_brightness / 255)))
                self.strip.show()
                if self.breathe_brightness >= 255:
                    self.ws2812_breathe_flag = 1
            if (self.next - self.start > (wait_ms / 1000.0)) and (self.ws2812_breathe_flag == 1):
                self.start = self.next
                self.breathe_brightness = self.breathe_brightness - 1
                for i in range(self.strip.get_led_count()):
                    self.strip.set_led_rgb_data(i, (int(data[0] * self.breathe_brightness / 255), int(data[1] * self.breathe_brightness / 255), int(data[2] * self.breathe_brightness / 255)))
                self.strip.show()
                if self.breathe_brightness <= 0:
                    self.ws2812_breathe_flag = 0

    def rainbowCycle(self, wait_ms=20, iterations=5):
        """Draw rainbow that uniformly distributes itself across all pixels."""
        if not self.is_support_led_function:
            return
        else:
            self.next = time.time()
            if (self.next - self.start > wait_ms / 1000.0):
                self.start = self.next
                for i in range(self.strip.get_led_count()):
                    self.strip.set_led_rgb_data(i, self.wheel((int(i * 256 / self.strip.get_led_count()) + self.color_wheel_value) & 255))
                self.strip.show()
                self.color_wheel_value += 1
                if self.color_wheel_value >= 256:
                    self.iteration += 1
                    self.color_wheel_value = 0

    def theaterChaseRainbow(self, wait_ms=50):
        """Rainbow movie theater light style chaser animation."""
        if self.is_support_led_function == False:
            return
        else:
            led_count = self.strip.get_led_count()
            for j in range(64):
                for i in range(0, led_count, 1):
                    self.strip.set_led_rgb_data(i, self.wheel((i + j * 4) % 255))
                    self.strip.show()
                    time.sleep(wait_ms / 1000.0)
                    self.strip.set_led_rgb_data(i, (0, 0, 0))

    def ledIndex(self, index, R, G, B):
        """Set the color of specific LEDs based on the index."""
        if self.is_support_led_function == False:
            return
        else:
            color = (R, G, B)
            for i in range(4):
                if index & 0x01 == 1:
                    self.strip.set_led_rgb_data(i, color)
                    self.strip.show()
                index = index >> 1

# Main program logic follows:
if __name__ == '__main__':
    print('Program is starting ... ')
    led = Led()

    try:
        while True:
            print("Chaser animation")
            led.colorWipe((255, 0, 0))   # Red wipe
            led.colorWipe((0, 255, 0))   # Green wipe
            led.colorWipe((0, 0, 255))   # Blue wipe
            led.theaterChaseRainbow()
            print("Rainbow animation")
            led.rainbow()
            led.rainbowCycle()
            led.colorWipe((0, 0, 0), 10)  # Turn off all LEDs
    except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be executed.
        led.colorWipe((0, 0, 0), 10)
        print("\nEnd of program")