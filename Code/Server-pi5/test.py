import time
from Led import *
led=Led()
def test_Led():
    if(led.Ledsupported == 1):
        try:
            led.ledIndex(0x01,255,0,0)          #red
            led.ledIndex(0x02,0,255,0)          #green
            led.ledIndex(0x04,0,0,255)          #blue
            led.ledIndex(0x08,255,255,255)      #white
            print ("The LED has been lit, the color is red green blue white")
            time.sleep(3)               #wait 3s
            led.colorWipe(led.strip, Color(0,0,0))  #turn off the light
            print ("\nEnd of program")
        except KeyboardInterrupt:
            led.colorWipe(led.strip, Color(0,0,0))  #turn off the light
            print ("\nEnd of program")
    else:
        try:
            print ("\nRaspberry PI 5 is currently being used, which is unsupported hardware.")
        except KeyboardInterrupt:
            print ("\nEnd of program")
      
from Motor import *            
PWM=Motor()          
def test_Motor(): 
    try:
        PWM.setMotorModel(2000,2000)        #Forward
        print ("The car is moving forward")
        time.sleep(1)
        PWM.setMotorModel(-2000,-2000)      #Back
        print ("The car is going backwards")
        time.sleep(1)
        PWM.setMotorModel(-2000,2000)       #Left 
        print ("The car is turning left")
        time.sleep(1)
        PWM.setMotorModel(2000,-2000)       #Right 
        print ("The car is turning right")  
        time.sleep(1)
        PWM.setMotorModel(0,0)              #Stop
        print ("\nEnd of program")
    except KeyboardInterrupt:
        PWM.setMotorModel(0,0)              #Stop
        print ("\nEnd of program")

from Ultrasonic import *
ultrasonic=Ultrasonic()                
def test_Ultrasonic():
    try:
        while True:
            data=ultrasonic.get_distance()   #Get the value
            distance=int(data)
            print ("Obstacle distance is "+str(distance)+"CM")
            time.sleep(1)
    except KeyboardInterrupt:
        print ("\nEnd of program")

from Line_Tracking import *
line=Line_Tracking()
def test_Infrared():
    try:
        line.test_Infrared()
    except KeyboardInterrupt:
        print ("\nEnd of program")

from servo import *
from Led import *
import os
servo=Servo()
led=Led()
def test_Servo():
    with open("calibration.txt", "r") as file:  # open file
        data = file.read()  # Read the file
        #print(data)
    file.close()
    if(data=='ok'):
        try:
            while True:
                for i in range(90,150,1):
                    servo.setServoPwm('0',i)
                    time.sleep(0.01)
                for i in range(140,90,-1):
                    servo.setServoPwm('1',i)
                    time.sleep(0.01)
                for i in range(90,140,1):
                    servo.setServoPwm('1',i)
                    time.sleep(0.01)
                for i in range(150,90,-1):
                    servo.setServoPwm('0',i)
                    time.sleep(0.01)   
        except KeyboardInterrupt:
            servo.setServoPwm('0',90)
            servo.setServoPwm('1',140)
            print ("\nEnd of program")
    else:
        #led.colorWipe(led.strip, Color(255,0, 0)) # Red light 
        #time.sleep(0.5)
        #led.colorWipe(led.strip, Color(0,0, 0))   # Turn off the light
        print ("\nThe steering gear has not been calibrated, please try again after calibration.")

# Main program logic follows:
if __name__ == '__main__':

    print ('Program is starting ... ')
    import sys
    if len(sys.argv)<2:
        print ("Parameter error: Please assign the device")
        exit() 
    if sys.argv[1] == 'Led':
        test_Led()
    elif sys.argv[1] == 'Motor':
        test_Motor()
    elif sys.argv[1] == 'Ultrasonic':
        test_Ultrasonic()
    elif sys.argv[1] == 'Infrared':
        test_Infrared()        
    elif sys.argv[1] == 'Servo': 
        test_Servo()