from gpiozero import DistanceSensor
import time
from Motor import *
from servo import *
trigger_pin = 27
echo_pin    = 22
sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin ,max_distance=3)

class Ultrasonic:
    def __init__(self):        
        pass
   
    def get_distance(self):     # get the measurement results of ultrasonic module,with unit: cm
        distance_cm = sensor.distance * 100
        return  int(distance_cm)
    
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