#!/usr/bin/python3

import io         # used to create file streams
from io import open #read sensor data
import fcntl      # used to access I2C parameters like addresses
import time       # used for sleep delay and timestamps
import string     # helps parse strings
import struct     # packs data for mqtt
import Adafruit_DHT as DHT #sensor module
import glob #pathing
import paho.mqtt.client as mqtt #mqtt client module
from influxdb import InfluxDBClient

#influxdb setup
host = "192.168.1.187" # influxdb server address
port = 8086 # default port
user = "admin" # the user/password created for the pi, with write access
password = "admin" 
dbname = "sensor_data" # the database we created earlier
measurement = "System1"
location = "flower"
clientinf = InfluxDBClient(host, port, user, password, dbname)

#Sensor setup
THsensor = DHT.DHT22 #air sendor type
THpin = 22 #air sensor pin
base_dir = '/sys/bus/w1/devices/' #1w device location
device_folder = glob.glob(base_dir + '28*')[0] #no idea
device_file = device_folder + '/w1_slave' #no idea

#mqtt setup
broker_address="test.mosquitto.org" #Mqtt broker address
topic = "home/grow/flower1"
clientid = 'jjust22a34'

#PH sensor code
class AtlasI2Cph:
    long_timeout = 1.5          # the timeout needed to query readings and calibrations
    short_timeout = .5          # timeout for regular commands
    default_bus = 1             # the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
    default_address = 99        # the default address for the sensor
    current_addr = default_address

    def __init__(self, address=default_address, bus=default_bus):
        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write
        self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
        self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

        # initializes I2C to either a user specified or default address
        self.set_i2c_address(address)

    def set_i2c_address(self, addr):
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        I2C_SLAVE = 0x703
        fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
        fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
        self.current_addr = addr

    def write(self, cmd):
        # appends the null character and sends the string over I2C
        cmd += "\00"
        self.file_write.write(cmd.encode('latin-1'))

    def read(self, num_of_bytes=31):
        # reads a specified number of bytes from I2C, then parses and displays the result
        res = self.file_read.read(num_of_bytes)         # read from the board
        if type(res[0]) is str:                 # if python2 read
            response = [i for i in res if i != '\x00']
            if ord(response[0]) == 1:             # if the response isn't an error
                # change MSB to 0 for all received characters except the first and get a list of characters
                # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                char_list = list(map(lambda x: chr(ord(x) & ~0x80), list(response[1:])))
                return ''.join(char_list)     # convert the char list to a string and returns it
            else:
                return "Error " + str(ord(response[0]))
                
        else:                                   # if python3 read
            if res[0] == 1: 
                # change MSB to 0 for all received characters except the first and get a list of characters
                # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                char_list = list(map(lambda x: chr(x & ~0x80), list(res[1:])))
                return ''.join(char_list)     # convert the char list to a string and returns it
            else:
                return "Error " + str(res[0])

    def query(self, string):
        # write a command to the board, wait the correct timeout, and read the response
        self.write(string)

        # the read and calibration commands require a longer timeout
        if((string.upper().startswith("R")) or
            (string.upper().startswith("CAL"))):
            time.sleep(self.long_timeout)
        elif string.upper().startswith("SLEEP"):
            return "sleep mode"
        else:
            time.sleep(self.short_timeout)

        return self.read()

    def close(self):
        self.file_read.close()
        self.file_write.close()

    def list_i2c_devices(self):
        prev_addr = self.current_addr # save the current address so we can restore it after
        i2c_devices = []
        for i in range (0,128):
            try:
                self.set_i2c_address(i)
                self.read(1)
                i2c_devices.append(i)
            except IOError:
                pass
        self.set_i2c_address(prev_addr) # restore the address we were using
        return i2c_devices

#EC sensor code
class AtlasI2Cec:
    long_timeout = 1.5          # the timeout needed to query readings and calibrations
    short_timeout = .5          # timeout for regular commands
    default_bus = 1             # the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
    default_address = 100        # the default address for the sensor
    current_addr = default_address

    def __init__(self, address=default_address, bus=default_bus):
        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write
        self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
        self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

        # initializes I2C to either a user specified or default address
        self.set_i2c_address(address)

    def set_i2c_address(self, addr):
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        I2C_SLAVE = 0x703
        fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
        fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
        self.current_addr = addr

    def write(self, cmd):
        # appends the null character and sends the string over I2C
        cmd += "\00"
        self.file_write.write(cmd.encode('latin-1'))

    def read(self, num_of_bytes=31):
        # reads a specified number of bytes from I2C, then parses and displays the result
        res = self.file_read.read(num_of_bytes)         # read from the board
        if type(res[0]) is str:                 # if python2 read
            response = [i for i in res if i != '\x00']
            if ord(response[0]) == 1:             # if the response isn't an error
                # change MSB to 0 for all received characters except the first and get a list of characters
                # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                char_list = list(map(lambda x: chr(ord(x) & ~0x80), list(response[1:])))
                return ''.join(char_list)     # convert the char list to a string and returns it
            else:
                return "Error " + str(ord(response[0]))
                
        else:                                   # if python3 read
            if res[0] == 1: 
                # change MSB to 0 for all received characters except the first and get a list of characters
                # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                char_list = list(map(lambda x: chr(x & ~0x80), list(res[1:])))
                return ''.join(char_list)     # convert the char list to a string and returns it
            else:
                return "Error " + str(res[0])

    def query(self, string):
        # write a command to the board, wait the correct timeout, and read the response
        self.write(string)

        # the read and calibration commands require a longer timeout
        if((string.upper().startswith("R")) or
            (string.upper().startswith("CAL"))):
            time.sleep(self.long_timeout)
        elif string.upper().startswith("SLEEP"):
            return "sleep mode"
        else:
            time.sleep(self.short_timeout)

        return self.read()

    def close(self):
        self.file_read.close()
        self.file_write.close()

    def list_i2c_devices(self):
        prev_addr = self.current_addr # save the current address so we can restore it after
        i2c_devices = []
        for i in range (0,128):
            try:
                self.set_i2c_address(i)
                self.read(1)
                i2c_devices.append(i)
            except IOError:
                pass
        self.set_i2c_address(prev_addr) # restore the address we were using
        return i2c_devices

#Water temp sensor code
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
#water temp sensor read code
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_f

#Main function,m publishes data from sensor
def publishdata(): #publishes the data to mqtt broker
    client = mqtt.Client(clientid) #create new instance
    client.connect(broker_address) #connect to broker
    client.subscribe(topic) #this should be a specific topic to each sensor
    client.publish(topic,getdata()) #publishes data to broker
    time.sleep(1) #waits for new data

#Pulls data from sensors
def getdata():
    phsense = AtlasI2Cph()
    ecsense = AtlasI2Cec()
    phs = phsense.query("R")
    time.sleep(1)
    h, t = DHT.read_retry(THsensor, THpin)
    time.sleep(1)
    f = t*9.0 / 5.0 + 32
    ecs = ecsense.query("R")
    time.sleep(1)
    wt = read_temp()
    ph = float(phs.rstrip('\x00'))
    ec = float(ecs.rstrip('\x00'))
    data = struct.pack('fffff',f,h,wt,ph,ec)
    iso = time.ctime()
    datal = [
        {
          "measurement": measurement,
              "tags": {
                  "location": location,
              },
              "time": iso,
              "fields": {
                  "temperature" : f,
                  "humidity": h,
                  "water temperature": wt,
                  "PH": ph,
                  "EC": ec
              }
          }
        ]
    clientinf.write_points(datal)
    return data

#main loop
def main():
    while True:
        publishdata()
          
if __name__ == '__main__':
    main()