import RPi.GPIO as GPIO
import time
import pigpio

class Servo:
    def __init__(self):
        self.channel1=7
        self.channel2=8
        self.channel3=25
        self.PwmServo = pigpio.pi()
        self.PwmServo.set_mode(self.channel1,pigpio.OUTPUT) 
        self.PwmServo.set_mode(self.channel2,pigpio.OUTPUT) 
        self.PwmServo.set_mode(self.channel3,pigpio.OUTPUT) 
        self.PwmServo.set_PWM_frequency(self.channel1,50)
        self.PwmServo.set_PWM_frequency(self.channel2,50)
        self.PwmServo.set_PWM_frequency(self.channel3,50)
        self.PwmServo.set_PWM_range(self.channel1, 4000)
        self.PwmServo.set_PWM_range(self.channel2, 4000)
        self.PwmServo.set_PWM_range(self.channel3, 4000)
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
            self.PwmServo.set_PWM_dutycycle(self.channel1,80+(400/180)*angle)
        elif channel=='1':
            angle=int(self.angle_range('1',angle))
            self.PwmServo.set_PWM_dutycycle(self.channel2,80+(400/180)*angle)
        elif channel=='2':
            angle=int(self.angle_range('2',angle))
            self.PwmServo.set_PWM_dutycycle(self.channel3,80+(400/180)*angle)

# Main program logic follows:
if __name__ == '__main__':
    print("Now servo 0 will be rotated to 150° and servos 1 will be rotated to 90°.") 
    print("If they were already at 150° and 90°, nothing would be observed.")
    print("Please keep the program running when installing the servos.")
    print("After that, you can press ctrl-C to end the program.")
    servo=Servo() 
    while True:
        try :
            servo.setServoPwm('0',150)
            servo.setServoPwm('1',90)           
        except KeyboardInterrupt:
            for i in range(150,90,-1):
                servo.setServoPwm('0',i)
                time.sleep(0.01)
            for i in range(90,140,1):
                servo.setServoPwm('1',i)
                time.sleep(0.01)
            print ("\nEnd of program")
            break