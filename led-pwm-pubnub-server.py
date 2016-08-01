# -*- coding: utf-8 -*-
from pubnub import Pubnub
import RPi.GPIO as GPIO
import time
import sys
import math
import threading

#Global constants
SECONDS_IN_ONE_MINUTE = 60

#General settings
debug = False

#Model
p = None

autostop_timer = None

speed_step_percentage = 10
max_speed_percentage = 70
current_speed_percentage = 0
speed_step_inc_pause = 1
speed_step_dec_pause = 1

is_started = False
is_stopped = False
is_changing_speed = False

max_exercise_time = SECONDS_IN_ONE_MINUTE

def pump_init():
    global p
    
    p = GPIO.PWM(26, 50)

def pump_start():
    global is_started, is_stopped
    
    if (is_started):
        print 'pump is already started'

        return

    is_stopped = False

    print 'starting water pump...'

    p.start(0)

    pump_change_speed_linear(max_speed_percentage)

    is_started = True

def pump_stop():
    global is_stopped, is_started
    
    if (is_stopped):
        print 'pump is already stopped'

        return

    is_started = False
    
    pump_change_speed_linear(0)

    p.stop()

    print 'water pump stopped'

    is_stopped = True

def pump_change_speed_linear(new_speed_percentage):
    if (is_stopped):
        print 'cannot change pump speed because it is stopped'

        return
    
    if (new_speed_percentage == current_speed_percentage):
        print 'pump speed is already ' + str(new_speed_percentage) + '%'
        
        return

    global is_changing_speed

    if (is_changing_speed):
        print 'pump is already changing speed'

        return

    is_changing_speed = True

    if (new_speed_percentage < current_speed_percentage):
        pump_dec_speed_linear(new_speed_percentage)
    else:
        pump_inc_speed_linear(new_speed_percentage)

    is_changing_speed = False

def pump_inc_speed_linear(target_speed_percentage):
    for new_speed_percentage in range(current_speed_percentage + speed_step_percentage, target_speed_percentage, speed_step_percentage):
        pump_set_speed(new_speed_percentage)

        time.sleep(speed_step_inc_pause)

    pump_set_speed(target_speed_percentage)

def pump_dec_speed_linear(target_speed_percentage):
    for new_speed_percentage in range(current_speed_percentage - speed_step_percentage, target_speed_percentage, -speed_step_percentage):
        pump_set_speed(new_speed_percentage)

        time.sleep(speed_step_dec_pause)

    pump_set_speed(target_speed_percentage)
    
def pump_set_speed(percentage):
    p.ChangeDutyCycle(percentage)

    print 'water pump speed set to ' + str(percentage) + '%'
    
    global current_speed_percentage
    current_speed_percentage = percentage

def autostop_timer_activate():
    global autostop_timer

    if (autostop_timer != None):
        print 'autostop timer already activated'

        return

    def callback():
        print 'automatically stopping water pump...'

        pump_stop()

    print 'activating autostop timer to fire in ' + str(max_exercise_time) + 's...'

    autostop_timer = threading.Timer(max_exercise_time, callback)
    autostop_timer.start()

def autostop_timer_deactivate():
    global autostop_timer
    
    if (autostop_timer == None):
        print 'autostop timer already deactivated'

        return

    autostop_timer.cancel()
    autostop_timer = None
    
    print 'autostop timer deactivated'

#Controllers
def start():
    print 'manually starting water pump...'

    #TODO: move to model
    autostop_timer_activate()    

    pump_start()

def set_speed(percentage):
    print 'manually changing water pump speed to ' + str(percentage) + '...'
    
    pump_change_speed_linear(percentage)

def stop():
    print 'manually stopping water pump...'
    
    pump_stop()

    #TODO: move to model
    autostop_timer_deactivate()

def heartbeat():
    pubnub.publish(
       channel = 'status',
       message = {
           'resource': 'heartbeat',
           'operation': 'status',
           'params': 'good'
        }
    )

dispatcher = {
    'water_pump': {
        'start': start,
        'set_speed': set_speed,
        'stop': stop
    },
    'heartbeat': {
        'status': heartbeat
    }
}
                          
#Routing
def route(request):
    resource = request['resource']
    operation = request['operation']
    params = request['params']

    if resource not in dispatcher:
        print 'Cannot find resource "' + resource + '"'

        return

    if operation not in dispatcher[resource]:
        print 'Cannot find operation "' + operation + '" for resource "' + resource + '"'

        return
    
    controller = dispatcher[resource][operation]

    if (params != None):
        controller(params)
    else:
        controller()

#Setup PubNub
pubnub = Pubnub(
    publish_key = 'pub-c-202f92c7-77aa-4abd-a588-edea3cbb4ee5',
    subscribe_key = 'sub-c-d379b9a0-573c-11e6-b1c5-0619f8945a4f'
)
channel = 'control'

def callback(message, channel):
    if (debug):
        print('[' + channel + ']: ' + str(message))

    route(message)

def error(message):
    print("ERROR: " + str(message))
  
def connect(message):
    print("CONNECTED")
  
def reconnect(message):
    print("RECONNECTED")
  
def disconnect(message):
    print("DISCONNECTED")  
  
pubnub.subscribe(
    channels = channel,
    callback = callback,
    error = error,
    connect = connect,
    reconnect = reconnect,
    disconnect = disconnect
)

def teardownPubNub():
    pubnub.unsubscribe(
        channel = channel
    )

#GPIO
def setupGPIO():
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(26, GPIO.OUT)

    GPIO.output(26, GPIO.LOW)

def teardownGPIO():
    GPIO.cleanup()

#Main
def main():
    setupGPIO()

    #model init
    pump_init()
    
    try:
        while True:
            time.sleep(5000)         
    except KeyboardInterrupt:
        pass

    teardownGPIO()
    teardownPubNub()

    sys.exit(0)

main()
