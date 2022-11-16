#!/usr/bin/python 
# -*- coding: utf-8 -*-
import numpy as np
import cv2
import socket
import io
import sys
import struct
from PIL import Image
import os
from threading import Timer
from threading import Thread
import threading

class VideoStreaming:
    def __init__(self):
        self.video_Flag=True
        self.connect_Flag=False
        self.face_x=0
        self.face_y=0

    def StartTcpClient1(self,IP):
        self.client_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def StartTcpClient(self, IP):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def StopTcpcClient(self):
        try:
            self.client_socket.shutdown(2)
            self.client_socket.close()
        except:
            pass
    def StopTcpcClient1(self):
        try:
            self.client_socket1.shutdown(2)
            self.client_socket1.close()
        except:
            pass

    def IsValidImage4Bytes(self,buf):
        bValid = True
        if buf[6:10] in (b'JFIF', b'Exif'):
            if not buf.rstrip(b'\0\r\n').endswith(b'\xff\xd9'):

                bValid = False
        else:
            try:
                Image.open(io.BytesIO(buf)).verify()
            except:
                bValid = False
        return bValid


    def face_detect(self,img):
        if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
            video = img
            #gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            gray = img
            faces = self.face_cascade.detectMultiScale(gray,1.2,3)
            if len(faces)>0 :
                for (x,y,w,h) in faces:
                    self.face_x=float(x+w/2.0)
                    self.face_y=float(y+h/2.0)
                    video = cv2.flip(video, -1)
                    img= cv2.rectangle(img, (x-10,y-10), (w+h+10,y+h+10), (0, 255, 0), 2)
            else:
                self.face_x=0
                self.face_y=0

    def streaming(self,ip):
        stream_bytes = b' '
        try:
            self.client_socket.connect((ip, 8003))
            self.connection = self.client_socket.makefile('rb')
        except:
            pass
        while True:
            try:
                stream_bytes= self.connection.read(4)
                leng=struct.unpack('<L', stream_bytes[:4])
                jpg=self.connection.read(leng[0])
                if self.IsValidImage4Bytes(jpg):
                    if self.video_Flag:
                        self.image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)  # 加载彩色图片
                        self.video_Flag=False
                    #self.face_detect(self.image)
            except Exception as e:
                print (e)
                break

    def sendData(self,s):
        if self.connect_Flag:
            self.client_socket1.send(s.encode('utf-8'))

    def recvData(self):
        data=""
        try:
            data=self.client_socket1.recv(1024).decode('utf-8')
        except:
            pass
        return data

    def socket1_connect(self,ip):
        try:
            self.client_socket1.connect((ip, 5003))
            self.connect_Flag=True
            print ("Connecttion Successful !")
        except Exception as e:
            print ("Connect to server Faild!: Server IP is right? Server is opend?")
            self.connect_Flag=False

if __name__ == '__main__':
    pass

