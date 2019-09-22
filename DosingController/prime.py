#!/usr/bin/python3

import RPi.GPIO as GPIO
import time

phup=17
phdown=27
a=22
b=5
cal=6
early=13
mid=19
guard=26

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