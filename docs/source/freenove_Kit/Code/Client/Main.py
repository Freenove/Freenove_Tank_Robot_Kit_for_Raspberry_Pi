#!/usr/bin/python
# -*- coding: utf-8 -*-
import numpy as np
import cv2
import socket
import os
import io
import time
import imghdr
import sys
from threading import Timer
from threading import Thread
from PIL import Image
import string
import math

from PID import *
from Command import COMMAND as cmd
from Thread import *
from threading import Thread
from Client_Ui import Ui_Client
from Video import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

class mywindow(QMainWindow,Ui_Client):
    def __init__(self):
        global timer
        super(mywindow,self).__init__()
        self.setupUi(self)
        self.img = QImage()
        self.img.load("*.png")
        self.img.save("*.png")
        self.img.load("*.jpg")
        self.img.save("*.jpg")
        self.setWindowIcon(QIcon('image/logo_Mini.png'))
        self.label_Video.setPixmap(QPixmap('image/Tank_Robot.png'))
        self.endChar='\n'
        self.intervalChar='#'
        self.h=self.IP.text()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.time)
        self.TCP=VideoStreaming()
        self.commandFlag = 1
        self.W_flag = 0
        self.Pinch_Flag = 0
        self.Drop_Flag = 0
        self.servo1=90
        self.servo2=140
        self.ws2812_number=15
        self.m_DragPosition=self.pos()
        self.setMouseTracking(True)
        self.Key_W=False
        self.Key_A=False
        self.Key_S=False
        self.Key_D=False

        self.pid = Incremental_PID(1, 0, 0.0025)
        file = open('IP.txt', 'r')
        self.IP.setText(str(file.readline()))
        file.close()

        self.camera_angle = 0
        self.color_custom_flag = False
        self.color_custom_flag2 = False
        self.color_select_button = 0
        self.color_red =   [0, 118, 31, 6, 255, 255]
        self.color_green = [50, 143, 129, 60, 255, 255]
        self.color_blue =  [100, 94, 142, 120, 255, 255]

        self.setFocusPolicy(Qt.StrongFocus)
        self.name.setAlignment(QtCore.Qt.AlignCenter)
        self.label_Servo1.setText('90')
        self.label_Servo2.setText('140')
        self.label_Video.setAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
        self.label_Servo1.setAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)
        self.label_Servo2.setAlignment(QtCore.Qt.AlignCenter|QtCore.Qt.AlignVCenter)

        self.HSlider_Servo1.setMinimum(90)
        self.HSlider_Servo1.setMaximum(150)
        self.HSlider_Servo1.setSingleStep(1)
        self.HSlider_Servo1.setValue(self.servo1)
        self.HSlider_Servo1.valueChanged.connect(self.Change_Left_Right)

        self.VSlider_Servo2.setMinimum(90)
        self.VSlider_Servo2.setMaximum(150)
        self.VSlider_Servo2.setSingleStep(1)
        self.VSlider_Servo2.setValue(self.servo2)
        self.VSlider_Servo2.valueChanged.connect(self.Change_Up_Down)

        self.Btn_Mode1.setChecked(True)
        self.Btn_Mode1.toggled.connect(lambda:self.on_btn_Mode(self.Btn_Mode1))
        self.Btn_Mode2.setChecked(False)
        self.Btn_Mode2.toggled.connect(lambda:self.on_btn_Mode(self.Btn_Mode2))
        self.Btn_Mode3.setChecked(False)
        self.Btn_Mode3.toggled.connect(lambda:self.on_btn_Mode(self.Btn_Mode3))

        self.Ultrasonic.clicked.connect(self.on_btn_Ultrasonic)

        self.checkBox_Led_Mode1.setChecked(False)
        self.checkBox_Led_Mode1.stateChanged.connect(lambda: self.LedChange(self.checkBox_Led_Mode1))
        self.checkBox_Led_Mode2.setChecked(False)
        self.checkBox_Led_Mode2.stateChanged.connect(lambda: self.LedChange(self.checkBox_Led_Mode2))
        self.checkBox_Led_Mode3.setChecked(False)
        self.checkBox_Led_Mode3.stateChanged.connect(lambda: self.LedChange(self.checkBox_Led_Mode3))
        self.checkBox_Led_Mode4.setChecked(False)
        self.checkBox_Led_Mode4.stateChanged.connect(lambda: self.LedChange(self.checkBox_Led_Mode4))

        self.checkBox_Pinch_Object.setChecked(False)
        self.checkBox_Pinch_Object.stateChanged.connect(lambda: self.SerovChange(self.checkBox_Pinch_Object))
        self.checkBox_Drop_Object.setChecked(False)
        self.checkBox_Drop_Object.stateChanged.connect(lambda: self.SerovChange(self.checkBox_Drop_Object))

        self.Led_Module.clicked.connect(lambda: self.LedChange(self.Led_Module))
        self.RGB.clicked.connect(lambda: self.LedChange(self.RGB))
        self.W.clicked.connect(self.ALL_Click)

        self.Color_W.textChanged.connect(lambda: self.WS2812_Text_Change())
        self.L1.clicked.connect(self.WS2812_Calculate)
        self.L2.clicked.connect(self.WS2812_Calculate)
        self.L3.clicked.connect(self.WS2812_Calculate)
        self.L4.clicked.connect(self.WS2812_Calculate)

        self.Btn_ForWard.pressed.connect(self.on_btn_ForWard)
        self.Btn_ForWard.released.connect(self.on_btn_Stop)
        self.Btn_Turn_Left.pressed.connect(self.on_btn_Turn_Left)
        self.Btn_Turn_Left.released.connect(self.on_btn_Stop)
        self.Btn_BackWard.pressed.connect(self.on_btn_BackWard)
        self.Btn_BackWard.released.connect(self.on_btn_Stop)
        self.Btn_Turn_Right.pressed.connect(self.on_btn_Turn_Right)
        self.Btn_Turn_Right.released.connect(self.on_btn_Stop)

        self.Btn_Video.clicked.connect(self.on_btn_video)
        self.Btn_Up.clicked.connect(self.on_btn_Up)
        self.Btn_Left.clicked.connect(self.on_btn_Left)
        self.Btn_Down.clicked.connect(self.on_btn_Down)
        self.Btn_Home.clicked.connect(self.on_btn_Home)
        self.Btn_Right.clicked.connect(self.on_btn_Right)

        self.Btn_Connect.clicked.connect(self.on_btn_Connect)
        self.Window_Min.clicked.connect(self.windowMinimumed)
        self.Window_Close.clicked.connect(self.close)

        self.hs_color_1.setMinimum(0)
        self.hs_color_1.setMaximum(180)
        self.hs_color_4.setMinimum(0)
        self.hs_color_4.setMaximum(180)

        self.hs_color_1.valueChanged.connect(lambda: self.ColorShow(self.hs_color_1))
        self.hs_color_2.valueChanged.connect(lambda: self.ColorShow(self.hs_color_2))
        self.hs_color_3.valueChanged.connect(lambda: self.ColorShow(self.hs_color_3))
        self.hs_color_4.valueChanged.connect(lambda: self.ColorShow(self.hs_color_4))
        self.hs_color_5.valueChanged.connect(lambda: self.ColorShow(self.hs_color_5))
        self.hs_color_6.valueChanged.connect(lambda: self.ColorShow(self.hs_color_6))
        self.Button_Color_Target_Red.clicked.connect(lambda: self.ColorShow(self.Button_Color_Target_Red))
        self.Button_Color_Target_Green.clicked.connect(lambda: self.ColorShow(self.Button_Color_Target_Green))
        self.Button_Color_Target_Blue.clicked.connect(lambda: self.ColorShow(self.Button_Color_Target_Blue))
        self.Button_Color_Target_Custom.clicked.connect(lambda: self.ColorShow(self.Button_Color_Target_Custom))
        self.color_hs_enable(False)

    def color_hs_enable(self,bool):
        self.hs_color_1.setEnabled(bool)
        self.hs_color_2.setEnabled(bool)
        self.hs_color_3.setEnabled(bool)
        self.hs_color_4.setEnabled(bool)
        self.hs_color_5.setEnabled(bool)
        self.hs_color_6.setEnabled(bool)

    def ColorShow(self,part):
        if part.objectName() == "hs_color_1":
            self.lineEdit_Color_1.setText(str(self.hs_color_1.value()))
            if self.color_select_button == 1:
                self.color_red[0] = self.hs_color_1.value()
            elif self.color_select_button == 2:
                self.color_green[0] = self.hs_color_1.value()
            elif self.color_select_button == 3:
                self.color_blue[0] = self.hs_color_1.value()
        elif part.objectName() == "hs_color_2":
            self.lineEdit_Color_2.setText(str(self.hs_color_2.value()))
            if self.color_select_button == 1:
                self.color_red[1] = self.hs_color_2.value()
            elif self.color_select_button == 2:
                self.color_green[1] = self.hs_color_2.value()
            elif self.color_select_button == 3:
                self.color_blue[1] = self.hs_color_2.value()
        elif part.objectName() == "hs_color_3":
            self.lineEdit_Color_3.setText(str(self.hs_color_3.value()))
            if self.color_select_button == 1:
                self.color_red[2] = self.hs_color_3.value()
            elif self.color_select_button == 2:
                self.color_green[2] = self.hs_color_3.value()
            elif self.color_select_button == 3:
                self.color_blue[2] = self.hs_color_3.value()
        elif part.objectName() == "hs_color_4":
            self.lineEdit_Color_4.setText(str(self.hs_color_4.value()))
            if self.color_select_button == 1:
                self.color_red[3] = self.hs_color_4.value()
            elif self.color_select_button == 2:
                self.color_green[3] = self.hs_color_4.value()
            elif self.color_select_button == 3:
                self.color_blue[3] = self.hs_color_4.value()
        elif part.objectName() == "hs_color_5":
            self.lineEdit_Color_5.setText(str(self.hs_color_5.value()))
            if self.color_select_button == 1:
                self.color_red[4] = self.hs_color_5.value()
            elif self.color_select_button == 2:
                self.color_green[4] = self.hs_color_5.value()
            elif self.color_select_button == 3:
                self.color_blue[4] = self.hs_color_5.value()
        elif part.objectName() == "hs_color_6":
            self.lineEdit_Color_6.setText(str(self.hs_color_6.value()))
            if self.color_select_button == 1:
                self.color_red[5] = self.hs_color_6.value()
            elif self.color_select_button == 2:
                self.color_green[5] = self.hs_color_6.value()
            elif self.color_select_button == 3:
                self.color_blue[5] = self.hs_color_6.value()
        elif part.objectName() == "Button_Color_Target_Red":
            if self.color_select_button != 1:
                self.color_select_button = 1
                self.Button_Color_Target_Red.setStyleSheet("color: rgb(255, 255, 0);")
                self.Button_Color_Target_Green.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Blue.setStyleSheet("color: rgb(220, 220, 220);")
            else:
                self.TCP.sendData(cmd.CMD_MOTOR + self.intervalChar + str(0) + self.intervalChar + str(0) + self.endChar)
                self.color_select_button = 0
                self.Button_Color_Target_Red.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Green.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Blue.setStyleSheet("color: rgb(220, 220, 220);")
                cv2.destroyAllWindows()
            self.hs_color_1.setValue(self.color_red[0])
            self.hs_color_2.setValue(self.color_red[1])
            self.hs_color_3.setValue(self.color_red[2])
            self.hs_color_4.setValue(self.color_red[3])
            self.hs_color_5.setValue(self.color_red[4])
            self.hs_color_6.setValue(self.color_red[5])
            self.lineEdit_Color_1.setText(str(self.hs_color_1.value()))
            self.lineEdit_Color_2.setText(str(self.hs_color_2.value()))
            self.lineEdit_Color_3.setText(str(self.hs_color_3.value()))
            self.lineEdit_Color_4.setText(str(self.hs_color_4.value()))
            self.lineEdit_Color_5.setText(str(self.hs_color_5.value()))
            self.lineEdit_Color_6.setText(str(self.hs_color_6.value()))
        elif part.objectName() == "Button_Color_Target_Green":
            if self.color_select_button != 2:
                self.color_select_button = 2
                self.Button_Color_Target_Green.setStyleSheet("color: rgb(255, 255, 0);")
                self.Button_Color_Target_Red.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Blue.setStyleSheet("color: rgb(220, 220, 220);")
            else:
                self.TCP.sendData(cmd.CMD_MOTOR + self.intervalChar + str(0) + self.intervalChar + str(0) + self.endChar)
                self.color_select_button = 0
                self.Button_Color_Target_Green.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Red.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Blue.setStyleSheet("color: rgb(220, 220, 220);")
                cv2.destroyAllWindows()
            self.hs_color_1.setValue(self.color_green[0])
            self.hs_color_2.setValue(self.color_green[1])
            self.hs_color_3.setValue(self.color_green[2])
            self.hs_color_4.setValue(self.color_green[3])
            self.hs_color_5.setValue(self.color_green[4])
            self.hs_color_6.setValue(self.color_green[5])
            self.lineEdit_Color_1.setText(str(self.hs_color_1.value()))
            self.lineEdit_Color_2.setText(str(self.hs_color_2.value()))
            self.lineEdit_Color_3.setText(str(self.hs_color_3.value()))
            self.lineEdit_Color_4.setText(str(self.hs_color_4.value()))
            self.lineEdit_Color_5.setText(str(self.hs_color_5.value()))
            self.lineEdit_Color_6.setText(str(self.hs_color_6.value()))
        elif part.objectName() == "Button_Color_Target_Blue":
            if self.color_select_button != 3:
                self.color_select_button = 3
                self.Button_Color_Target_Blue.setStyleSheet("color: rgb(255, 255, 0);")
                self.Button_Color_Target_Red.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Green.setStyleSheet("color: rgb(220, 220, 220);")
            else:
                self.TCP.sendData(cmd.CMD_MOTOR + self.intervalChar + str(0) + self.intervalChar + str(0) + self.endChar)
                self.color_select_button = 0
                self.Button_Color_Target_Blue.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Red.setStyleSheet("color: rgb(220, 220, 220);")
                self.Button_Color_Target_Green.setStyleSheet("color: rgb(220, 220, 220);")
                cv2.destroyAllWindows()
            self.hs_color_1.setValue(self.color_blue[0])
            self.hs_color_2.setValue(self.color_blue[1])
            self.hs_color_3.setValue(self.color_blue[2])
            self.hs_color_4.setValue(self.color_blue[3])
            self.hs_color_5.setValue(self.color_blue[4])
            self.hs_color_6.setValue(self.color_blue[5])
            self.lineEdit_Color_1.setText(str(self.hs_color_1.value()))
            self.lineEdit_Color_2.setText(str(self.hs_color_2.value()))
            self.lineEdit_Color_3.setText(str(self.hs_color_3.value()))
            self.lineEdit_Color_4.setText(str(self.hs_color_4.value()))
            self.lineEdit_Color_5.setText(str(self.hs_color_5.value()))
            self.lineEdit_Color_6.setText(str(self.hs_color_6.value()))
        elif part.objectName() == "Button_Color_Target_Custom":
            if self.color_custom_flag is False:
                self.color_custom_flag = True
                self.Button_Color_Target_Custom.setStyleSheet("color: rgb(255, 255, 0);")
                self.label_color_1.setStyleSheet("color: rgb(255, 255, 0);")
                self.label_color_2.setStyleSheet("color: rgb(255, 255, 0);")
                self.label_color_3.setStyleSheet("color: rgb(255, 255, 0);")
                self.label_color_4.setStyleSheet("color: rgb(255, 255, 0);")
                self.label_color_5.setStyleSheet("color: rgb(255, 255, 0);")
                self.label_color_6.setStyleSheet("color: rgb(255, 255, 0);")
            else:
                self.Button_Color_Target_Custom.setStyleSheet("color: rgb(220, 220, 220);")
                self.label_color_1.setStyleSheet("color: rgb(220, 220, 220);")
                self.label_color_2.setStyleSheet("color: rgb(220, 220, 220);")
                self.label_color_3.setStyleSheet("color: rgb(220, 220, 220);")
                self.label_color_4.setStyleSheet("color: rgb(220, 220, 220);")
                self.label_color_5.setStyleSheet("color: rgb(220, 220, 220);")
                self.label_color_6.setStyleSheet("color: rgb(220, 220, 220);")
                self.color_custom_flag = False
            self.color_hs_enable(self.color_custom_flag)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() and Qt.LeftButton:
            self.move(QMouseEvent.globalPos() - self.m_DragPosition)
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_drag = False

    def keyPressEvent(self, event):
        if(event.key() == Qt.Key_Up):
            self.on_btn_Up()
        elif(event.key() == Qt.Key_Left):
            self.on_btn_Left()
        elif(event.key() == Qt.Key_Down):
            self.on_btn_Down()
        elif(event.key() == Qt.Key_Right):
            self.on_btn_Right()
        elif(event.key() == Qt.Key_Home):
            self.on_btn_Home()

        if(event.key() == Qt.Key_Q):
            if self.Btn_Mode1.isChecked() == True:
                self.Btn_Mode2.setChecked(True)
            elif self.Btn_Mode2.isChecked() == True:
                self.Btn_Mode3.setChecked(True)
            elif self.Btn_Mode3.isChecked() == True:
                self.Btn_Mode1.setChecked(True)

        if(event.key() == Qt.Key_L):
            if  self.checkBox_Led_Mode1.isChecked() == True:
                self.checkBox_Led_Mode2.setChecked(True)
            elif  self.checkBox_Led_Mode2.isChecked() == True:
                self.checkBox_Led_Mode3.setChecked(True)
            elif  self.checkBox_Led_Mode3.isChecked() == True:
                self.checkBox_Led_Mode4.setChecked(True)
            elif  self.checkBox_Led_Mode4.isChecked() == True:
                self.checkBox_Led_Mode4.setChecked(False)
            elif  self.checkBox_Led_Mode4.isChecked() == False:
                self.checkBox_Led_Mode1.setChecked(True)

        if(event.key() == Qt.Key_C):
            self.on_btn_Connect()
        if(event.key() == Qt.Key_V):
            self.on_btn_video()

        if (event.key() == Qt.Key_O):
            if self.checkBox_Pinch_Object.isChecked() == True:
                self.checkBox_Pinch_Object.setChecked(False)
            else:
                self.checkBox_Pinch_Object.setChecked(True)

        if (event.key() == Qt.Key_P):
            if self.checkBox_Drop_Object.isChecked() == True:
                self.checkBox_Drop_Object.setChecked(False)
            else:
                self.checkBox_Drop_Object.setChecked(True)

        if event.isAutoRepeat():
            pass
        else :
            if event.key() == Qt.Key_W:
                self.on_btn_ForWard()
                self.Key_W=True
            elif event.key() == Qt.Key_S:
                self.on_btn_BackWard()
                self.Key_S=True
            elif event.key() == Qt.Key_A:
                self.on_btn_Turn_Left()
                self.Key_A=True
            elif event.key() == Qt.Key_D:
                self.on_btn_Turn_Right()
                self.Key_D=True

    def closeEvent(self, event):
        self.timer.stop()
        try:
            stop_thread(self.recv)
            stop_thread(self.streaming)
        except:
            pass
        self.TCP.StopTcpcClient()
        try:
            os.remove("video.jpg")
        except:
            pass
        QCoreApplication.instance().quit()
        os._exit(0)

    def keyReleaseEvent(self, event):

        if(event.key() == Qt.Key_W):
            time.sleep(0.05)
            if(event.key() == Qt.Key_W):
                if not(event.isAutoRepeat()) and self.Key_W==True:
                    self.on_btn_Stop()
                    self.Key_W=False
        elif(event.key() == Qt.Key_A):
            if not(event.isAutoRepeat()) and self.Key_A==True:
                self.on_btn_Stop()
                self.Key_A=False
        elif(event.key() == Qt.Key_S):
            if not(event.isAutoRepeat()) and self.Key_S==True:
                self.on_btn_Stop()
                self.Key_S=False
        elif(event.key() == Qt.Key_D):
            if not(event.isAutoRepeat()) and self.Key_D==True:
                self.on_btn_Stop()
                self.Key_D=False

    def on_btn_ForWard(self):
        ForWard=self.intervalChar+str(2000)+self.intervalChar+str(2000)+self.endChar
        self.TCP.sendData(cmd.CMD_MOTOR+ForWard)

    def on_btn_Turn_Left(self):
        Turn_Left=self.intervalChar+str(-2000)+self.intervalChar+str(2000)+self.endChar
        self.TCP.sendData(cmd.CMD_MOTOR+ Turn_Left)

    def on_btn_BackWard(self):
        BackWard=self.intervalChar+str(-2000)+self.intervalChar+str(-2000)+self.endChar
        self.TCP.sendData(cmd.CMD_MOTOR+BackWard)

    def on_btn_Turn_Right(self):
        Turn_Right=self.intervalChar+str(2000)+self.intervalChar+str(-2000)+self.endChar
        self.TCP.sendData(cmd.CMD_MOTOR+Turn_Right)

    def on_btn_Stop(self):
        Stop=self.intervalChar+str(0)+self.intervalChar+str(0)+self.endChar
        self.TCP.sendData(cmd.CMD_MOTOR+Stop)

    def on_btn_Up(self):
        self.servo2=self.servo2+5
        if self.servo2>=150:
            self.servo2=150
        self.VSlider_Servo2.setValue(self.servo2)

    def on_btn_Left(self):
        self.servo1=self.servo1-5
        if self.servo1<=90:
            self.servo1=90
        self.HSlider_Servo1.setValue(self.servo1)

    def on_btn_Down(self):
        self.servo2=self.servo2-5
        if self.servo2<=90:
            self.servo2=90
        self.VSlider_Servo2.setValue(self.servo2)

    def on_btn_Right(self):
        self.servo1=self.servo1+5
        if self.servo1>=150:
            self.servo1=150
        self.HSlider_Servo1.setValue(self.servo1)

    def on_btn_Home(self):
        self.servo1=90
        self.servo2=140
        self.HSlider_Servo1.setValue(self.servo1)
        self.VSlider_Servo2.setValue(self.servo2)

    def on_btn_Ultrasonic(self):
        if self.Ultrasonic.text()=="Ultrasonic":
            self.TCP.sendData(cmd.CMD_SONIC +self.intervalChar+self.endChar)
        else:
            self.TCP.sendData(cmd.CMD_SONIC+self.intervalChar+'0'+self.endChar)
            self.Ultrasonic.setText("Ultrasonic")

    def Change_Left_Right(self):#Left or Right
        self.servo1=self.HSlider_Servo1.value()
        self.TCP.sendData(cmd.CMD_SERVO+self.intervalChar+'0'+self.intervalChar+str(self.servo1)+self.endChar)
        self.label_Servo1.setText("%d"%self.servo1)
    def Change_Up_Down(self):#Up or Down
        self.servo2=self.VSlider_Servo2.value()
        self.TCP.sendData(cmd.CMD_SERVO+self.intervalChar+'1'+self.intervalChar+str(self.servo2)+self.endChar)
        self.label_Servo2.setText("%d"%self.servo2)

    def windowMinimumed(self):
        self.showMinimized()

    def WS2812_Text_Change(self):
        if self.Color_W.text()=='':
            self.Color_W.setText('0')
        ws2812_w = int(self.Color_W.text())
        if ws2812_w >= 16:
            ws2812_w=15
            self.Color_W.setText(str(ws2812_w))
        if ws2812_w & 0x001 == 0x001:
            self.L1.setChecked(True)
        else:
            self.L1.setChecked(False)
        if ws2812_w & 0x002 == 0x002:
            self.L2.setChecked(True)
        else:
            self.L2.setChecked(False)
        if ws2812_w & 0x004 == 0x004:
            self.L3.setChecked(True)
        else:
            self.L3.setChecked(False)
        if ws2812_w & 0x008 == 0x008:
            self.L4.setChecked(True)
        else:
            self.L4.setChecked(False)

    def ALL_Click(self):
        R = self.Color_R.text()
        G = self.Color_G.text()
        B = self.Color_B.text()
        All_led = '15'
        led_Off = self.intervalChar + str(0) + self.intervalChar + str(0) + self.intervalChar + str(0)
        color = self.intervalChar + str(R) + self.intervalChar + str(G) + self.intervalChar + str(B)
        if self.W_flag==0:
            self.W_flag =1
            self.L1.setChecked(False)
            self.L2.setChecked(False)
            self.L3.setChecked(False)
            self.L4.setChecked(False)
            self.Color_W.setText("0")
            self.TCP.sendData(cmd.CMD_LED + self.intervalChar + '0' + color + self.intervalChar + self.Color_W.text() + self.endChar)
        else:
            self.W_flag = 0
            self.L1.setChecked(True)
            self.L2.setChecked(True)
            self.L3.setChecked(True)
            self.L4.setChecked(True)
            self.Color_W.setText("15")
            self.TCP.sendData(cmd.CMD_LED + self.intervalChar + '1' + color + self.intervalChar + self.Color_W.text() + self.endChar)
    def WS2812_Calculate(self):
        if self.L1.isChecked() == True:
            self.ws2812_number=self.ws2812_number|0x01
        else:
            self.ws2812_number = self.ws2812_number & 0xffe
        if self.L2.isChecked() == True:
            self.ws2812_number = self.ws2812_number | 0x02
        else:
            self.ws2812_number = self.ws2812_number & 0xffd
        if self.L3.isChecked() == True:
            self.ws2812_number=self.ws2812_number|0x04
        else:
            self.ws2812_number = self.ws2812_number & 0xffb
        if self.L4.isChecked() == True:
            self.ws2812_number=self.ws2812_number|0x08
        else:
            self.ws2812_number = self.ws2812_number & 0xff7
        self.Color_W.setText(str(self.ws2812_number))

    def LedChange(self,b):
        R=self.Color_R.text()
        G=self.Color_G.text()
        B=self.Color_B.text()
        All_led='15'
        led_Off = self.intervalChar + str(0) + self.intervalChar + str(0) + self.intervalChar + str(0)
        color = self.intervalChar + str(R )+ self.intervalChar + str(G) + self.intervalChar + str(B)
        if b.text() == "RGB":
            color_palette = QColorDialog.getColor().name()
            self.Color_R.setText(str(int(color_palette[1:3], 16)))
            self.Color_G.setText(str(int(color_palette[3:5], 16)))
            self.Color_B.setText(str(int(color_palette[5:7], 16)))
        if b.text() == "Led_Module":
            if self.commandFlag:
                self.TCP.sendData(cmd.CMD_LED + self.intervalChar + '0' + color + self.intervalChar + self.Color_W.text() + self.endChar)
                time.sleep(0.05)
                self.TCP.sendData(cmd.CMD_LED + self.intervalChar + '1' + color + self.intervalChar + self.Color_W.text()+ self.endChar)
        if b.text() == "Led_Mode1":
           if b.isChecked() == True:
               self.checkBox_Led_Mode2.setChecked(False)
               self.checkBox_Led_Mode3.setChecked(False)
               self.checkBox_Led_Mode4.setChecked(False)
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED + self.intervalChar + '2' + color + self.intervalChar + self.Color_W.text() + self.endChar)
           else:
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED+self.intervalChar+'0'+color + self.intervalChar + self.Color_W.text() + self.endChar)
        if b.text() == "Led_Mode2":
           if b.isChecked() == True:
               self.checkBox_Led_Mode1.setChecked(False)
               self.checkBox_Led_Mode3.setChecked(False)
               self.checkBox_Led_Mode4.setChecked(False)
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED+self.intervalChar+'3'+color + self.intervalChar + self.Color_W.text()+ self.endChar)
           else:
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED+self.intervalChar+'0'+color + self.intervalChar + self.Color_W.text()+ self.endChar)
        if b.text() == "Led_Mode3":
           if b.isChecked() == True:
               self.checkBox_Led_Mode2.setChecked(False)
               self.checkBox_Led_Mode1.setChecked(False)
               self.checkBox_Led_Mode4.setChecked(False)
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED + self.intervalChar + '4' + color + self.intervalChar + All_led+ self.endChar)
           else:
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED+self.intervalChar+'0'+color + self.intervalChar + self.Color_W.text()+ self.endChar)
        if b.text() == "Led_Mode4":
           if b.isChecked() == True:
               self.checkBox_Led_Mode2.setChecked(False)
               self.checkBox_Led_Mode3.setChecked(False)
               self.checkBox_Led_Mode1.setChecked(False)
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED+self.intervalChar+'5'+color + self.intervalChar + self.Color_W.text()+ self.endChar)
           else:
               if self.commandFlag:
                   self.TCP.sendData(cmd.CMD_LED+self.intervalChar+'0'+color + self.intervalChar + self.Color_W.text()+ self.endChar)

    def SerovChange(self, b):
        if b.text() == "Pinch_Object":
            if b.isChecked() == True:
                self.Pinch_Flag=1
                self.checkBox_Drop_Object.setChecked(False)
            else:
                self.Pinch_Flag = 0
        if b.text() == "Drop_Object":
            if b.isChecked() == True:
                self.Drop_Flag = 1
                self.checkBox_Pinch_Object.setChecked(False)
            else:
                self.Drop_Flag = 0
        if (self.Pinch_Flag ==1):
            self.TCP.sendData(cmd.CMD_ACTION + self.intervalChar + '1' + self.endChar)
        elif (self.Drop_Flag == 1):
            self.TCP.sendData(cmd.CMD_ACTION + self.intervalChar + '2' + self.endChar)
        elif (self.Pinch_Flag ==0) and (self.Drop_Flag ==0):
            self.TCP.sendData(cmd.CMD_ACTION + self.intervalChar + '0' + self.endChar)
            pass

    def on_btn_Mode(self,Mode):
        if Mode.text() == "M-Free":
            if Mode.isChecked() == True:
                #self.timer.start(34)
                self.TCP.sendData(cmd.CMD_MODE+self.intervalChar+'0'+self.endChar)
        elif Mode.text() == "M-Sonic":
            if Mode.isChecked() == True:
                #self.timer.stop()
                self.TCP.sendData(cmd.CMD_MODE+self.intervalChar+'1'+self.endChar)
        elif Mode.text() == "M-Line":
            if Mode.isChecked() == True:
                #self.timer.stop()
                self.TCP.sendData(cmd.CMD_MODE+self.intervalChar+'2'+self.endChar)

    def on_btn_video(self):
        if self.Btn_Video.text()=='Open Video':
            self.timer.start(10)
            if self.TCP.connect_Flag == True:
                self.h = self.IP.text()
                self.TCP.StartTcpClient(self.h, )
                try:
                    self.streaming=Thread(target=self.TCP.streaming,args=(self.h,))
                    self.streaming.start()
                except:
                    print ('video error')
            self.Btn_Video.setText('Close Video')
        elif self.Btn_Video.text()=='Close Video':
            self.timer.stop()
            try:
                stop_thread(self.streaming)
            except:
                pass
            self.TCP.StopTcpcClient()
            self.Btn_Video.setText('Open Video')

    def on_btn_Connect(self):
        file = open('IP.txt', 'w')
        file.write(self.IP.text())
        file.close()
        if self.Btn_Connect.text() == "Connect":
            self.h=self.IP.text()
            self.TCP.StartTcpClient1(self.h,)
            try:
                self.recv=Thread(target=self.recvmassage)
                self.recv.start()
            except:
                print ('recv error')
            print ('Server address:'+str(self.h)+'\n')
            self.Btn_Connect.setText("Disconnect")
        elif self.Btn_Connect.text()=="Disconnect":
            self.Btn_Connect.setText( "Connect")
            self.TCP.connect_Flag = False
            try:
                stop_thread(self.recv)
            except:
                pass
            self.TCP.StopTcpcClient1()

    def close(self):
        self.timer.stop()
        try:
            stop_thread(self.recv)
            stop_thread(self.streaming)
        except:
            pass
        self.TCP.StopTcpcClient1()
        try:
            os.remove("video.jpg")
        except:
            pass
        QCoreApplication.instance().quit()
        os._exit(0)

    def recvmassage(self):
            self.TCP.socket1_connect(self.h)
            restCmd=""
            while True:
                Alldata=restCmd+str(self.TCP.recvData())
                restCmd=""
                print (Alldata)
                if Alldata=="":
                    break
                else:
                    cmdArray=Alldata.split("\n")
                    if(cmdArray[-1] != ""):
                        restCmd=cmdArray[-1]
                        cmdArray=cmdArray[:-1]
                for oneCmd in cmdArray:
                    Massage=oneCmd.split("#")
                    if cmd.CMD_SONIC in Massage:
                        self.Ultrasonic.setText('Obstruction:%s cm'%Massage[1])
                    elif cmd.CMD_ACTION in Massage:
                        if Massage[1]=='10':
                            self.checkBox_Pinch_Object.setChecked(False)
                        elif Massage[1] == '20':
                            self.checkBox_Drop_Object.setChecked(False)

    def block_detect(self,video):
        try:
            cv2.cvtColor(video, cv2.COLOR_RGB2GRAY)
            gs_frame = cv2.GaussianBlur(video, (5, 5), 0)
            gs_frame = cv2.cvtColor(gs_frame, cv2.COLOR_BGR2HSV)
            gs_frame = cv2.erode(gs_frame, (5, 5), iterations=1)
            gs_frame = cv2.dilate(gs_frame, (2, 2), iterations=1)

            if self.color_select_button == 1:
                inRange_hsv = cv2.inRange(gs_frame, (self.color_red[0], self.color_red[1], self.color_red[2]),(self.color_red[3], self.color_red[4], self.color_red[5]))
            elif self.color_select_button == 2:
                inRange_hsv = cv2.inRange(gs_frame, (self.color_green[0], self.color_green[1], self.color_green[2]),(self.color_green[3], self.color_green[4], self.color_green[5]))
            elif self.color_select_button == 3:
                inRange_hsv = cv2.inRange(gs_frame, (self.color_blue[0], self.color_blue[1], self.color_blue[2]),(self.color_blue[3], self.color_blue[4], self.color_blue[5]))
            cv2.imshow("Image", inRange_hsv)
            cnts = cv2.findContours(inRange_hsv.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
            c = max(cnts, key=cv2.contourArea)
            rect = cv2.minAreaRect(c)
            center = None
            radius = 0
            X, Y = rect[0]
            if len(cnts) > 0:
                c = max(cnts, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                M = cv2.moments(c)
                if M["m00"] > 0:
                    center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                    if radius < 10:
                        center = None
            if center != None:
                D = round(1660 / (2 * radius))  # CM
                x = self.pid.PID_compute(center[0])
                d = self.pid.PID_compute(D)
                if radius > 15:
                    cv2.circle(video, (int(X), int(Y)), 3, (255, 0, 0),5)
                    cv2.circle(video, (int(X), int(Y)), int(radius), (0, 255, 0), 2)
                    if d < 14:
                        self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(-1200) + '#' + str(-1200) + self.endChar)
                    elif d > 20:
                        self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(1200) + '#' + str(1200) + self.endChar)
                    else:
                        if x < 85:
                            self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(-1350) + '#' + str(1350) + self.endChar)
                        elif x > 315:
                            self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(1350) + '#' + str(-1350) + self.endChar)
                        else:
                            self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(0) + '#' + str(0) + self.endChar)
                else:
                    self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(0) + '#' + str(0) + self.endChar)
            else:
                self.TCP.sendData(cmd.CMD_MOTOR + '#' + str(0) + '#' + str(0) + self.endChar)
        except:
            pass

    def time(self):
        try:
            if self.TCP.video_Flag == False:
                video = self.TCP.image
                height, width, bytesPerComponent = video.shape
                if self.color_select_button != 0:
                    self.block_detect(video)
                video = cv2.cvtColor(video, cv2.COLOR_BGR2RGB, video)
                QImg =  QImage(video.data, width, height, 3 * width, QImage.Format_RGB888)
                self.label_Video.setPixmap(QPixmap.fromImage(QImg))
                self.TCP.video_Flag = True
        except Exception as e:
            print(e)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    myshow=mywindow()
    myshow.show()
    sys.exit(app.exec_())