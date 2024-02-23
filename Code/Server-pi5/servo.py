from gpiozero import AngularServo
import time
import warnings
from gpiozero import PWMSoftwareFallback
warnings.filterwarnings("ignore", category=PWMSoftwareFallback)

channel1=25
channel2=7
channel3=8
SERVO_DELAY_SEC = 0.001 
myCorrection=0.0
maxPW=(2.5+myCorrection)/1000
minPW=(0.5-myCorrection)/1000
servo1 =  AngularServo(channel1,initial_angle=0,min_angle=0, max_angle=180,min_pulse_width=minPW,max_pulse_width=maxPW)
servo2 =  AngularServo(channel2,initial_angle=0,min_angle=0, max_angle=180,min_pulse_width=minPW,max_pulse_width=maxPW)
servo3 =  AngularServo(channel3,initial_angle=0,min_angle=0, max_angle=180,min_pulse_width=minPW,max_pulse_width=maxPW)

class Servo:
    def __init__(self):
        pass
    def angle_range(self,channel,init_angle):
        if channel=='0':
            if init_angle<90 :
                init_angle=90
            elif init_angle>150 :
                init_angle=150
            else:
                init_angle=init_angle
        elif channel=='1':
            if init_angle<90 :
                init_angle=90
            elif init_angle>150 :
                init_angle=150
            else:
                init_angle=init_angle
        elif channel=='2':
            if init_angle<0 :
                init_angle=0
            elif init_angle>180 :
                init_angle=180
            else:
                init_angle=init_angle
        return init_angle
        
    def setServoPwm(self,channel,angle):
        if channel=='0':
            angle=int(self.angle_range('0',angle))
            servo1.angle = angle
        elif channel=='1':
            angle=int(self.angle_range('1',angle))
            servo2.angle = angle
        elif channel=='2':
            angle=int(self.angle_range('2',angle))
            servo3.angle = angle

# Main program logic follows:
if __name__ == '__main__':
    
    print("Now servo 0 will be rotated to 150° and servos 1 will be rotated to 90°.") 
    print("If they were already at 150° and 90°, nothing would be observed.")
    print("Please keep the program running when installing the servos.")
    print("After that, you can press ctrl-C to end the program.")
    servo=Servo() 
    file = open('calibration.txt', 'w')
    file.write('ok')
    file.close()
    while True:
        try :
            servo.setServoPwm('0',150)
            servo.setServoPwm('1',90)  
            time.sleep(1)            
        except KeyboardInterrupt:
            for i in range(150,90,-1):
                servo.setServoPwm('0',i)
                time.sleep(0.01)
            for i in range(90,140,1):
                servo.setServoPwm('1',i)
                time.sleep(0.01)
            print ("\nEnd of program")
            break