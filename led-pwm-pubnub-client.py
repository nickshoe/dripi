from pubnub import Pubnub
import time
import threading

debug = False

pubnub = Pubnub(
    publish_key = 'pub-c-202f92c7-77aa-4abd-a588-edea3cbb4ee5',
    subscribe_key = 'sub-c-d379b9a0-573c-11e6-b1c5-0619f8945a4f'
)
channel = 'control'

def send_message(message):
    pubnub.publish(
        channel = channel,
        message = message
    )

#Heartbeat
heartbeat_watch_timer = None
heartbeat_countdown_timer = None

def heartbeat_read():
    send_message({
        'resource': 'heartbeat',
        'operation': 'status',
        'params': None
    })
    
    start_heartbeat_countdown()

def start_heartbeat_countdown():
    global heartbeat_countdown_timer
    
    heartbeat_countdown_timer = threading.Timer(5.0, no_heartbeat_callback)
    heartbeat_countdown_timer.start()

def no_heartbeat_callback():
    print 'server could be down, not received heartbeat within 5s'

    start_heartbeat_watch()

def stop_heartbeat_countdown():
    global heartbeat_countdown_timer

    heartbeat_countdown_timer.cancel()
    heartbeat_countdown_timer = None

def start_heartbeat_watch():    
    global heartbeat_watch_timer

    heartbeat_watch_timer = threading.Timer(7.0, heartbeat_read)
    heartbeat_watch_timer.start()

def stop_heartbeat_watch():
    global heartbeat_watch_timer

    heartbeat_watch_timer.cancel()
    heartbeat_watch_timer = None

def heartbeat_callback(message, channel):
    stop_heartbeat_countdown()

    if debug:
        print 'server is healty, received its heartbeat (' + message['params'] + ')'

    start_heartbeat_watch()

pubnub.subscribe(
    channels = 'status',
    callback = heartbeat_callback
)

heartbeat_read()

#Water Pump Control
start_message = {
    'resource': 'water_pump',
    'operation': 'start',
    'params': None
}

stop_message = {
    'resource': 'water_pump',
    'operation': 'stop',
    'params': None
}

while True:

##    print 'Sending start command to water pump'
##    send_message(start_message)
##
##    time.sleep(5)
##
##    print 'Sending set speed to 100 command to water pump'
##    send_message({
##        'resource': 'water_pump',
##        'operation': 'set_speed',
##        'params': 100
##    })
##
##    time.sleep(5)
##
##    print 'Sending stop command to water pump'
##    send_message(stop_message)
##
##    time.sleep(5)

    send_message({
        'resource': 'pi',
        'operation': 'status',
        'params': None
    })

    time.sleep(5)
