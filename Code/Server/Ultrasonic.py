import RPi.GPIO as GPIO
import time
from Motor import *
from servo import *

class Ultrasonic:
    def __init__(self):        
        GPIO.setwarnings(False)        
        self.trigger_pin = 27
        self.echo_pin = 22
        self.MAX_DISTANCE = 300               # define the maximum measuring distance, unit: cm
        self.timeOut = self.MAX_DISTANCE*60   # calculate timeout according to the maximum measuring distance
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_pin,GPIO.OUT)
        GPIO.setup(self.echo_pin,GPIO.IN)
        
    def pulseIn(self,pin,level,timeOut): # obtain pulse time of a pin under timeOut
        t0 = time.time()
        while(GPIO.input(pin) != level):
            if((time.time() - t0) > timeOut*0.000001):
                return 0;
        t0 = time.time()
        while(GPIO.input(pin) == level):
            if((time.time() - t0) > timeOut*0.000001):
                return 0;
        pulseTime = (time.time() - t0)*1000000
        return pulseTime
    
    def get_distance(self):     # get the measurement results of ultrasonic module,with unit: cm
        distance_cm2=[0.0,0.0,0.0,0.0,0.0]
        for i in range(5):
            GPIO.output(self.trigger_pin,GPIO.HIGH)      # make trigger_pin output 10us HIGH level 
            time.sleep(0.00001)     # 10us
            GPIO.output(self.trigger_pin,GPIO.LOW) # make trigger_pin output LOW level 
            pingTime = self.pulseIn(self.echo_pin,GPIO.HIGH,self.timeOut)   # read plus time of echo_pin
            distance_cm2[i] = pingTime * 340.0 / 2.0 / 10000.0     # calculate distance with sound speed 340m/s
        distance_cm2=sorted(distance_cm2)
        return  distance_cm2[2]
    
    def run_motor(self,distance):
        if(distance!=0):
            if distance < 45 :
                self.PWM.setMotorModel(-1500,-1500) #Back
                time.sleep(0.4)
                self.PWM.setMotorModel(-1500,1500)  #Left
                time.sleep(0.2)         
            else :
                self.PWM.setMotorModel(1500,1500)   #Forward
            
    def run(self):
        self.PWM=Motor()
        while True:
            distance = self.get_distance()
            time.sleep(0.2)
            #print ("The distance is "+str(distance)+"CM")
            self.run_motor(distance)

ultrasonic=Ultrasonic()         
if __name__ == '__main__':     # Program entrance
    print ('Program is starting...')
    servo=Servo()
    servo.setServoPwm('0',90)
    servo.setServoPwm('1',140)
    try:
        ultrasonic.run()
    except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
        PWM.setMotorModel(0,0)
        servo.setServoPwm('0',90)
        servo.setServoPwm('1',140)
        print ("\nEnd of program")