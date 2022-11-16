#!/usr/bin/python 
# -*- coding: utf-8 -*-
import io
import socket
import struct
import time
from picamera2 import Picamera2,Preview
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.encoders import Quality
from libcamera import Transform
from threading import Condition
import fcntl
import  sys
import threading
from Motor import *
from servo import *
from Led import *
from Thread import *
from Action import *
from Remove_Obstacles import *
from Ultrasonic import *
from Line_Tracking import *
from threading import Timer
from threading import Thread
from Command import COMMAND as cmd

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class Server:   
    def __init__(self):
        self.PWM=Motor()
        self.servo=Servo()
        self.servo.setServoPwm('0',90)
        self.servo.setServoPwm('1',140)
        
        self.led=Led()
        self.ultrasonic=Ultrasonic()
        self.servoMode=ServoMode()
        self.infrared=Line_Tracking()
        self.auto_Clear=Remove_Obstacles()
        
        self.tcp_Flag = True
        self.sonic=False
        self.ACTION=False
        
        self.Mode = '0'
        self.endChar='\n'
        self.intervalChar='#'
    def get_interface_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                            0x8915,
                                            struct.pack('256s',b'wlan0'[:15])
                                            )[20:24])
    def StartTcpServer(self):
        HOST=str(self.get_interface_ip())
        self.server_socket1 = socket.socket()
        self.server_socket1.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
        self.server_socket1.bind((HOST, 5003))
        self.server_socket1.listen(1)
        self.server_socket = socket.socket()
        self.server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
        self.server_socket.bind((HOST, 8003))              
        self.server_socket.listen(1)
        print('Server address: '+HOST)
        
    def StopTcpServer(self):
        try:
            self.connection.close()
            self.connection1.close()
            self.stopMode()
        except Exception as e:
            self.stopMode()
            print ('\n'+"No client connection")
            
    def Reset(self):
        self.resetVideoThread()
        self.resetCmdThread()

    def resetCmdThread(self):
        HOST=str(self.get_interface_ip())
        try:
            self.connection1.close()
        except :
            pass
        self.server_socket1 = socket.socket()
        self.server_socket1.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
        self.server_socket1.bind((HOST, 5003))
        self.server_socket1.listen(1)
        
        self.ReadData=Thread(target=self.readdata)
        self.ReadData.start()
    def resetVideoThread(self):
        HOST=str(self.get_interface_ip())
        try:
            self.connection.close()
        except :
            pass
        self.server_socket = socket.socket()
        self.server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
        self.server_socket.bind((HOST, 8003))              
        self.server_socket.listen(1)
        
        self.SendVideo=Thread(target=self.sendvideo)
        self.SendVideo.start()
        
    def send(self,data):
        self.connection1.send(data.encode('utf-8'))    
    def sendvideo(self):
        try:
            self.connection,self.client_address = self.server_socket.accept()
            self.connection=self.connection.makefile('wb')
        except:
            pass
        self.server_socket.close()
        print ("socket video connected ... ")
        camera = Picamera2()
        camera.configure(camera.create_video_configuration(main={"size": (400, 300)},transform=Transform(hflip=1,vflip=1)))
        output = StreamingOutput()
        encoder = JpegEncoder(q=90)
        camera.start_recording(encoder, FileOutput(output),quality=Quality.VERY_HIGH) 
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            try:                
                lenFrame = len(output.frame) 
                #print("output .length:",lenFrame)
                lengthBin = struct.pack('<I', lenFrame)
                self.connection.write(lengthBin)
                self.connection.write(frame)
            except Exception as e:
                camera.stop_recording()
                camera.close()
                print ("End transmit ... " )
                self.resetVideoThread()
                break
                 
    def stopMode(self):
        try:
            stop_thread(self.ultrasonicTimer)
            self.PWM.setMotorModel(0,0)
        except:
            pass
        try:
            stop_thread(self.Led_Mode)
        except:
            pass
        try:
            stop_thread(self.auto_ClearRun)
            self.PWM.setMotorModel(0,0)
        except:
            pass
        
        try:
            stop_thread(self.ultrasonicRun)
            self.PWM.setMotorModel(0,0)
            self.led.ledIndex(15,0,0,0)
            self.servo.setServoPwm('0',90)
            self.servo.setServoPwm('1',140)
        except:
            pass
        
    def readdata(self):
        try:
            try:
                self.connection1,self.client_address1 = self.server_socket1.accept()
                print ("Client connection successful !")
            except:
                print ("Client connect failed")
            restCmd=""
            self.server_socket1.close()
            while True:
                try:
                    AllData=restCmd+self.connection1.recv(1024).decode('utf-8')
                except:
                    if self.tcp_Flag:
                        self.Reset()
                    break
                print(AllData)
                if len(AllData) < 5:
                    restCmd=AllData
                    if restCmd=='' and self.tcp_Flag:
                        self.Reset()
                        break
                restCmd=""
                if AllData=='':
                    break
                else:
                    cmdArray=AllData.split("\n")
                    if(cmdArray[-1] != ""):
                        restCmd=cmdArray[-1]
                        cmdArray=cmdArray[:-1]
                
                for oneCmd in cmdArray:
                    data=oneCmd.split("#")
                    if cmd.CMD_MODE in data:
                        if data[1]=='0' :
                            self.stopMode()
                            self.Mode='0'
                            self.sonic=False

                        elif data[1]=='1' :
                            self.stopMode()
                            self.Mode='1'
                            self.ultrasonicRun=threading.Thread(target=self.ultrasonic.run)
                            self.ultrasonicRun.start()
                            self.sonic=True
                            self.ultrasonicTimer = threading.Timer(0.5,self.sendUltrasonic)
                            self.ultrasonicTimer.start()
                            
                        elif data[1]=='2' :
                            self.stopMode()
                            self.Mode='2'
                            self.auto_ClearRun=Thread(target=self.auto_Clear.run)
                            self.auto_ClearRun.start()
                            self.sonic=True
                            self.ultrasonicTimer = threading.Timer(0.5,self.sendUltrasonic)
                            self.ultrasonicTimer.start()
                            
                    elif (cmd.CMD_MOTOR in data) and self.Mode=='0':
                        try:
                            data1=int(data[1])
                            data2=int(data[2])

                            if data1==None or data2==None :
                                continue
                            self.PWM.setMotorModel(data1,data2)
                        except:
                            pass
                    elif cmd.CMD_SERVO in data:
                        try:
                            data1=data[1]
                            data2=int(data[2])
                            if data1==None or data2==None:
                                continue
                            self.servo.setServoPwm(data1,data2)
                            
                        except:
                            pass
                    elif cmd.CMD_ACTION in data:
                        self.servoMode1=data[1]
                        if self.servoMode1== '0':
                            try:
                                stop_thread(servoMode)
                            except:
                                pass
                            self.servoMode.ServoMode(self.servoMode1)
                        elif self.servoMode1=='1'or self.servoMode1== '2':
                            try:
                                stop_thread(servoMode)
                            except:
                                pass
                            servoMode=Thread(target=self.servoMode.ServoMode,args=(data[1],))
                            servoMode.start()
                            self.ACTION=True
                            self.ACTIONTimer = threading.Timer(0.15,self.sendACTION)
                            self.ACTIONTimer.start() 
                            
                    elif cmd.CMD_LED in data:
                        try:
                            stop_thread(Led_Mode)
                        except:
                            pass
                        Led_Mode=Thread(target=self.led.ledMode,args=(data,))
                        Led_Mode.start()
                    elif cmd.CMD_SONIC in data:
                        self.sonic=True
                        self.ultrasonicTimer = threading.Timer(0.1,self.sendUltrasonic)
                        self.ultrasonicTimer.start()
                        if data[1]=='0':
                            self.sonic=False    
        except Exception as e:
            print(e)
        self.StopTcpServer()    
    def sendUltrasonic(self):
        if self.sonic==True:
            ADC_Ultrasonic=int(self.ultrasonic.get_distance())
            if ADC_Ultrasonic==int(self.ultrasonic.get_distance()):
                try:
                    if(ADC_Ultrasonic!=0):
                        self.send(cmd.CMD_SONIC+"#"+str(ADC_Ultrasonic)+'\n')
                except:
                    self.sonic=False
            self.ultrasonicTimer = threading.Timer(0.13,self.sendUltrasonic)
            self.ultrasonicTimer.start()
            
    def sendACTION(self):
        if self.ACTION==True:
            if self.servoMode.actionflag=='0':
                pass
            elif self.servoMode.actionflag=='10':
                try:
                    self.send(cmd.CMD_ACTION+"#"+'10'+'\n')
                    self.servoMode.actionflag='0'
                except:
                    self.ACTION=False
            elif self.servoMode.actionflag=='20':
                try:
                    self.send(cmd.CMD_ACTION+"#"+'20'+'\n')
                    self.servoMode.actionflag=='0'
                    self.ACTION=False
                except:
                    self.ACTION=False
            self.ACTIONTimer = threading.Timer(0.1,self.sendACTION)
            self.ACTIONTimer.start()
 
if __name__=='__main__':
    pass
