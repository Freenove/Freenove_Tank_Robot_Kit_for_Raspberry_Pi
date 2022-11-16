import RPi.GPIO as GPIO
import time
import pigpio
from servo import *
from Ultrasonic import *
from Motor import *

class ServoMode:
    def __init__(self):
        self.data=0
        self.actionflag='0'
        self.servo=Servo()
        self.distance=Ultrasonic()
        self.PWM=Motor()
    def send2(self,data):
        self.connection2.send(data.encode('utf-8'))         
    def ServoMode(self,n):
        self.mode=n
        while True:        
            if self.mode=='1':
                self.data=self.distance.get_distance()
                time.sleep(0.01)
                #print ("Obstacle distance is "+str(self.data)+"CM")
                if(self.data <=11 and self.data >5):
                    self.PWM.setMotorModel(0,0)
                    time.sleep(0.05)
                    if self.data <7.5 :
                        self.PWM.setMotorModel(-1300,-1300)
                    elif self.data >7.7 :
                        self.PWM.setMotorModel(1300,1300)
                    else:
                        self.PWM.setMotorModel(0,0)
                        for i in range(140,90,-1):
                            self.servo.setServoPwm('1',i)
                            time.sleep(0.01)
                        time.sleep(0.10)
                        for i in range(90,130,1):
                            self.servo.setServoPwm('0',i)
                            time.sleep(0.01)
                        time.sleep(0.10)
                        for i in range(90,140,1):
                            self.servo.setServoPwm('1',i)
                            time.sleep(0.01)
                        time.sleep(0.2)
                        self.mode='0'
                        self.actionflag='10'
                        time.sleep(0.1)
                        continue
                elif(self.data <6):
                    self.PWM.setMotorModel(-1200,-1200) 
                else:
                    self.PWM.setMotorModel(1200,1200)
                    
            elif self.mode=='2':
                self.PWM.setMotorModel(0,0)
                for i in range(140,90,-1):
                    self.servo.setServoPwm('1',i)
                    time.sleep(0.01)
                for i in range(130,90,-1):
                    self.servo.setServoPwm('0',i)
                    time.sleep(0.01)
                for i in range(90,140,1):
                    self.servo.setServoPwm('1',i)
                    time.sleep(0.01)
                self.mode='0'
                self.actionflag='20'
                time.sleep(0.10)
                
            elif self.mode=='0':
                self.PWM.setMotorModel(0,0)
                self.actionflag='0'
                break
            
action=ServoMode()
# Main program logic follows:
if __name__ == '__main__':
    print("Now servos will rotate to 90°.") 
    print("If they have already been at 90°, nothing will be observed.")
    print("Please keep the program running when installing the servos.")
    print("After that, you can press ctrl-C to end the program.")
    servo=Servo()
    while True: 
        try :
            servo.setServoPwm('0',90)
            servo.setServoPwm('1',140)
            
        except KeyboardInterrupt:
            self.PWM.setMotorModel(0,0)
            servo.setServoPwm('0',90)
            servo.setServoPwm('1',140)
            print ("\nEnd of program")
            break