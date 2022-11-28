# clean.py Test of asynchronous mqtt client with clean session.
# (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# Public brokers https://github.com/mqtt/mqtt.github.io/wiki/public_brokers

# The use of clean_session means that after a connection failure subscriptions
# must be renewed (MQTT spec 3.1.2.4). This is done by the connect handler.
# Note that publications issued during the outage will be missed. If this is
# an issue see unclean.py.

# red LED: ON == WiFi fail
# blue LED heartbeat: demonstrates scheduler is running.

#Import libraries - config.py sets up wifi and mqtt
from neopixel import Neopixel
from mqtt_as import MQTTClient, config
from config import wifi_led, blue_led  # Local definitions
import uasyncio as asyncio
import machine
from machine import Pin, PWM
from time import sleep
from time import gmtime
#from time import gmtime



# Set up Servo and Data Range
servoPin = PWM(Pin(16))
servoPin.freq(50)

servospeed = 0.05 #Speed of the servo movement - 0.05 provides a good smooth speed
servorange = 156#Edit for range of servo - 116 equates to approx 270 degrees with Open Gauges Gear Ratio
datarange = 360 #Data Range - in our case 60 for 0-60 MPH

# Calibrate data to degrees - Servo Range / Data Range (in our case Data Range is 60 for 0-60MPH)

datatodegrees = servorange/datarange

# Set up list for data and max/min/average as required
datalist = [0,0]


#Set up Neopixels
numpix = 65 #number of neopixels to the sweep the servo

pixels = Neopixel(numpix, 0, 28, "RGB")
YELLOW = (255, 100, 0)
ORANGE = (255, 50, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
OFF = (0, 0, 0)
WHITE = (50, 50, 50) #255 is full brightness - not recommended due to power draw

# Calibrate Pixels to Match Servo - Servo Range/Number of Pixels

def servo(degrees):
    # limit degrees beteen 0 and 180
    if degrees > 180: degrees=180
    if degrees < 0: degrees=0
    # set max and min duty
    #Reverse order to change direction according to servo
    
    maxDuty=1000
    minDuty=9000
    # new duty is between min and max duty in proportion to its value
    newDuty=minDuty+(maxDuty-minDuty)*(degrees/180)
    # servo PWM value is set
    servoPin.duty_u16(int(newDuty))
    
# First Sweep - Degree Range to be Edited According to Servo and Gear Ratio
def sweep():
    n= 0
    while n < servorange :
      
        servo(n)
        sleep(servospeed)
        n = n+1
        
    sleep(4)    
    n= servorange
    while n >= 0 :
      
        servo(n)
        sleep(servospeed)
        n = n-1

def lights():

    pixels.fill(WHITE)
    pixels.show()   



# Subscription callback
def sub_cb(topic, msg, retained):
    print(f'Topic: "{topic.decode()}" Message: "{msg.decode()}" Retained: {retained}')
    
    mqttdata = float(msg)
    print("Wind Speed =  ", mqttdata)
    degrees = mqttdata*datatodegrees
    print("Degrees Turned = ", datatodegrees)
    sleep(servospeed)
    datalist.append(degrees)
   
    if datalist[0] == datalist[-1]:
           
                sleep(2) 
    
        
    else:
        
        while datalist[0] >  datalist[-1]:
          
            servo(datalist[0])
            sleep(servospeed)
            datalist[0] = (datalist[0])-1
            
            if datalist[0] == datalist[-1]:
                sleep(2)
            
         
        while datalist[0] <  datalist[-1]:
         
            servo(datalist[0])
            sleep(servospeed)
            datalist[0] = (datalist[0])+1
            
            if datalist[0] == datalist[-1]:
                 sleep(2)
          
        if len(datalist) > 3:
            print ("Trimming List")
            del datalist[3]      
               
            print(datalist)
       
      

   
    
# Demonstrate scheduler is operational.
async def heartbeat():
    s = True
    while True:
        await asyncio.sleep_ms(500)
        blue_led(s)
        s = not s

async def wifi_han(state):
    wifi_led(not state)
    print('Wifi is ', 'up' if state else 'down')
    lights()
    sweep()
    await asyncio.sleep(1)

# If you connect with clean_session True, must re-subscribe (MQTT spec 3.1.2.4)
async def conn_han(client):
    await client.subscribe('personal/ucfnaps/downhamweather/windDir', 1)

async def main(client):
    try:
        await client.connect()
    except OSError:
        print('Connection failed.')
        machine.reset()
        return
    
    while True:
        await asyncio.sleep(5)
     

# Define configuration
config['subs_cb'] = sub_cb
config['wifi_coro'] = wifi_han
config['connect_coro'] = conn_han
config['clean'] = True

# Set up client
MQTTClient.DEBUG = True  # Optional
client = MQTTClient(config)

asyncio.create_task(heartbeat())


try:
    asyncio.run(main(client))
    

finally:
    client.close()  # Prevent LmacRxBlk:1 errors
    asyncio.new_event_loop()