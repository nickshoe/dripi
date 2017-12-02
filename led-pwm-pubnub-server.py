# -*- coding: utf-8 -*-
from pubnub import Pubnub
import RPi.GPIO as GPIO
import time
import sys
import math
import threading
import datetime
import subprocess
import re
import os

#Global constants
SECONDS_IN_ONE_MINUTE = 60
SECONDS_IN_ONE_HOUR = 60 * SECONDS_IN_ONE_MINUTE

#General settings
debug = False

#Model
gpio_bcm_pin = 25

#PWM driver
p = None

speed_step_percentage = 10
max_speed_percentage = 70
current_speed_percentage = 0
speed_step_inc_pause = 1
speed_step_dec_pause = 1

autostop_timer = None

is_running = False
is_changing_speed = False

last_started_at = None
last_stopped_at = None

max_exercise_time = SECONDS_IN_ONE_HOUR

def pump_init():
    GPIO.setup(gpio_bcm_pin, GPIO.OUT)

    GPIO.output(gpio_bcm_pin, GPIO.HIGH)
    
    #PWM driver
    #global p
    
    #p = GPIO.PWM(gpio_bcm_pin, 50)

def pump_start():
    global is_running, last_started_at
    
    if (is_running):
        print('pump is already started')

        return

    print('starting water pump...')

    #Relay driver
    GPIO.output(gpio_bcm_pin, GPIO.LOW)

    #PWM driver
    #p.start(0)

    #pump_change_speed_linear(max_speed_percentage)

    last_started_at = datetime.datetime.utcnow()

    is_running = True

def pump_stop():
    global is_running, last_stopped_at
    
    if (is_running == False):
        print('pump is already stopped')

        return

    #Relay driver
    GPIO.output(gpio_bcm_pin, GPIO.HIGH)

    #PWM driver
    #pump_change_speed_linear(0)

    #p.stop()

    print('water pump stopped')

    last_stopped_at = datetime.datetime.utcnow()

    is_running = False

def pump_change_speed_linear(new_speed_percentage):
    #Relay driver
    print('water pump driver is not PWM, is on/off')

    return

    #PWM driver
    if (is_running == False):
        print('cannot change pump speed because it is stopped')

        return
    
    if (new_speed_percentage == current_speed_percentage):
        print('pump speed is already ' + str(new_speed_percentage) + '%')
        
        return

    global is_changing_speed

    if (is_changing_speed):
        print('pump is already changing speed')

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

    print('water pump speed set to ' + str(percentage) + '%')
    
    global current_speed_percentage
    current_speed_percentage = percentage

def autostop_timer_activate():
    global autostop_timer

    if (autostop_timer != None):
        print('autostop timer already activated')

        return

    def callback():
        print('automatically stopping water pump...')

        pump_stop()

    print('activating autostop timer to fire in ' + str(max_exercise_time) + 's...')

    autostop_timer = threading.Timer(max_exercise_time, callback)
    autostop_timer.start()

def autostop_timer_deactivate():
    global autostop_timer
    
    if (autostop_timer == None):
        print('autostop timer already deactivated')

        return

    autostop_timer.cancel()
    autostop_timer = None
    
    print('autostop timer deactivated')

#Controllers
def start():
    print('manually starting water pump...')

    #TODO: move to model
    autostop_timer_activate()    

    pump_start()

def set_speed(percentage):
    print('manually changing water pump speed to ' + str(percentage) + '...')
    
    pump_change_speed_linear(percentage)

def stop():
    print('manually stopping water pump...')
    
    pump_stop()

    #TODO: move to model
    autostop_timer_deactivate()

def status():
    last_start = None
    if (last_started_at != None):
        last_start = last_started_at.isoformat()

    last_stop = None
    if (last_stopped_at != None):
        last_stop = last_stopped_at.isoformat()
    
    pubnub.publish(
        channel = 'status',
        message = {
            'resource': 'water_pump',
            'operation': 'status',
            'params': {
                'is_running': is_running,
                'max_exercise_time': max_exercise_time,
                'last_started_at': last_start,
                'last_stopped_at': last_stop
            }
        }
    )

def pi_status():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = dir_path + "/pi-temps.sh"
    
    try:
        bytes_output = subprocess.check_output(script_path)

        string_output = bytes_output.decode("utf-8")

        lines = string_output.splitlines()

        cpu_temp_string = lines[0].strip()
        gpu_temp_string = lines[1].strip()
        cpu_freq_string = lines[2].strip()

        cpu_temp_match = re.search('\d+\.\d', cpu_temp_string)
        gpu_temp_match = re.search('\d+\.\d', gpu_temp_string)
        cpu_freq_match = re.search('\d+', cpu_freq_string)

        cpu_temp = cpu_temp_match.group()
        gpu_temp = gpu_temp_match.group()
        cpu_freq = cpu_freq_match.group()

        pubnub.publish(
            channel = 'status',
            message = {
                'resource': 'pi',
                'operation': 'status',
                'params': {
                    'cpu_temp': cpu_temp,
                    'gpu_temp': gpu_temp,
                    'cpu_freq': cpu_freq
                }
            }
        )
    except FileNotFoundError:
        print('cannot find "' + script_path + '"')
    except subprocess.CalledProcessError:
        print('execution error "' + script_path + '"')

def pi_shutdown():
    try:
        bytes_output = subprocess.check_output(["sudo", "shutdown", "--poweroff"]) 

        string_output = bytes_output.decode("utf-8")

        pubnub.publish(
            channel = 'status',
            message = {
                'resource': 'pi',
                'operation': 'shutdown',
                'params': {
                    'wall_message': string_output
                }
            }
        )
    except FileNotFoundError:
        print('cannot find shutdonwn binary')
    except subprocess.CalledProcessError:
        print('shutdown execution error')

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
        'stop': stop,
        'status': status
    },
    'heartbeat': {
        'status': heartbeat
    },
    'pi': {
        'status': pi_status,
        'shutdown': pi_shutdown
    }
}
                          
#Routing
def route(request):
    resource = request['resource']
    operation = request['operation']
    params = request['params']

    if resource not in dispatcher:
        print('Cannot find resource "' + resource + '"')

        return

    if operation not in dispatcher[resource]:
        print('Cannot find operation "' + operation + '" for resource "' + resource + '"')

        return
    
    controller = dispatcher[resource][operation]

    if (params != None):
        controller(params)
    else:
        controller()

#Setup PubNub
pubnub = Pubnub(
    publish_key = 'pub-c-202f92c7-77aa-4abd-a588-edea3cbb4ee5',
    subscribe_key = 'sub-c-d379b9a0-573c-11e6-b1c5-0619f8945a4f',
    daemon = True
)
channel = 'control'

keep_alive_timer = None

def keep_alive_callback(time):
    print(time)

def keep_alive():
    pubnub.time(keep_alive_callback)

    schedule_next_keep_alive()

def schedule_next_keep_alive():
    keep_alive_timer = threading.Timer(30, keep_alive)
    keep_alive_timer.start()

def callback(message, channel):
    if (debug):
        print('[' + channel + ']: ' + str(message))

    route(message)

def error(message):
    print("ERROR: " + str(message))

def connect(message):
    print("CONNECTED")

    #keep_alive()
  
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
