#!/usr/bin/python3

import RPi.GPIO as GPIO
import time

phup=18
phdown=23
a=24
b=25
cal=12
early=16
mid=20
guard=21

chan_list = [phup,phdown,a,b,cal,early,mid,guard]
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(chan_list, GPIO.OUT)
GPIO.output(chan_list,GPIO.LOW)

t= int(input('Prime run time? '))

GPIO.output(chan_list,GPIO.HIGH)
time.sleep(t)
GPIO.output(chan_list,GPIO.LOW)
GPIO.cleanup