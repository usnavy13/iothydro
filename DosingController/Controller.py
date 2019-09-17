#!/usr/bin/python3

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt #mqtt client
import time
import struct #packing module
import configparser

#GPIO pin numbers
phup=17
phdown=27
a=22
b=5
cal=6
early=13
mid=19
guard=26

#Config setup
config = configparser.RawConfigParser()
config.read('controllerconfig.txt')

#Program settings
calmix = float(config.get('MIX', 'cal'))
abmix = float(config.get('MIX', 'ab'))
earlymix = float(config.get('MIX', 'early'))
midmix = float(config.get('MIX', 'mid'))
guardmix = float(config.get('MIX', 'guard'))
rate = float(config.get('MIX', 'rate'))
ecthresh = float(config.get('Thresh', 'ec'))
cycletime = float(config.get('Thresh', 'time'))
phupthresh = float(config.get('Thresh', 'phup'))
phlowthresh = float(config.get('Thresh', 'phlow'))
phupdose = float(config.get('MIX', 'phup'))
phdowndose = float(config.get('MIX', 'phdown'))
ph=6
ec=1500
count = 0

#GPIO setup
chan_list = [phup,phdown,a,b,cal,early,mid,guard]
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(chan_list, GPIO.OUT)
GPIO.output(chan_list,GPIO.LOW)

#MQTT client setup
client = mqtt.Client("controller1fhwgw") #create new instance
broker_address="test.mosquitto.org" #broker address
topic = "home/grow/flower1"
   
#Message function updates sensor data and resets failsafe counter
def on_message(client, userdata, message):
    data = message.payload #message from broker
    datau = struct.unpack('fffff', data) #unpacking data from sensor
    fr,hr,wtr,phr,ecr = datau #assigning temp and humidty values from data
    global ph
    global ec
    global count
    ph = round(phr,1)
    ec = round(ecr,2)
    count = 0
    #print('PH = ',ph,' EC = ',ec)
    
#MQTT function
def main():    
    client.on_message=on_message #run on message function when message recieved
    client.connect(broker_address) #connect to broker
    client.subscribe(topic)#subscribe to topic   
    client.loop_start() #run forever

#main loop
if __name__ == '__main__':
    main()
    while True:
        #PPM adjustments checks new message value and checks failsafe counter
        if ec <= ecthresh  and count <= 2:
            GPIO.output(cal,GPIO.HIGH)
            time.sleep(calmix / rate)
            GPIO.output(cal,GPIO.LOW)
            GPIO.output(a,GPIO.HIGH)
            GPIO.output(b,GPIO.HIGH)
            time.sleep(abmix / rate)
            GPIO.output(a,GPIO.LOW)
            GPIO.output(b,GPIO.LOW)
            GPIO.output(early,GPIO.HIGH)
            time.sleep(earlymix / rate)
            GPIO.output(early,GPIO.LOW)
            GPIO.output(mid,GPIO.HIGH)
            time.sleep(midmix / rate)
            GPIO.output(mid,GPIO.LOW)
            GPIO.output(guard,GPIO.HIGH)
            time.sleep(guardmix / rate)
            GPIO.output(guard,GPIO.LOW)
            time.sleep(cycletime)
            count += 1            
        #Lowers PH compares to upper threshold
        if ph >= phupthresh and count <= 2:
            GPIO.output(phdown,GPIO.HIGH)
            time.sleep(phdowndose / rate)
            GPIO.output(phdown,GPIO.LOW)
            time.sleep(cycletime)
            count += 1            
        #Raises PH compares to lower threshold
        if ph <= phlowthresh and count <= 2:
            GPIO.output(phup,GPIO.HIGH)
            time.sleep(phupdose / rate)
            GPIO.output(phup,GPIO.LOW)
            time.sleep(cycletime)
            count += 1
        
