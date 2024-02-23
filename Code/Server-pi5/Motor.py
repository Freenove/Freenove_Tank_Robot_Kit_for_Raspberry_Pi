from gpiozero import Motor
import time
left_motor = Motor(24, 23)
right_motor = Motor(5, 6)

class Motor:
    def __init__(self):
        pass

    def duty_range(self,duty1,duty2):
        if duty1>4095:
            duty1=4095
        elif duty1<-4095:
            duty1=-4095        
        if duty2>4095:
            duty2=4095
        elif duty2<-4095:
            duty2=-4095
        return duty1,duty2
    
    def left_Wheel(self,duty):
        if duty>0:
            left_motor.forward(duty/4096)
        elif duty<0:
            left_motor.backward(-duty/4096)
        else:
            left_motor.stop()

    def right_Wheel(self,duty):
        if duty>0:
            right_motor.forward(duty/4096)
        elif duty<0:
            right_motor.backward(-duty/4096)
        else:
            right_motor.stop()

    def setMotorModel(self,duty1,duty2):
        duty1,duty2=self.duty_range(duty1,duty2)
        self.left_Wheel(duty1)
        self.right_Wheel(duty2)
        
PWM=Motor()
def loop():
    PWM.setMotorModel(2000,2000)        #Forward
    time.sleep(1)
    PWM.setMotorModel(-2000,-2000)      #Back
    time.sleep(1)
    PWM.setMotorModel(2000,-2000)       #Left 
    time.sleep(1)
    PWM.setMotorModel(-2000,2000)       #Right    
    time.sleep(1)
    PWM.setMotorModel(0,0)          #Stop
    time.sleep(1)
    
def destroy():
    PWM.setMotorModel(0,0)

if __name__=='__main__':
    print ('Program is starting ... \n')
    try:
        loop()
    except KeyboardInterrupt:  # When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
        destroy()