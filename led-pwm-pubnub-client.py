from pubnub import Pubnub
import time
import timer

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

def start_heartbeat_watch():
    global heartbeat_watch_timer
    
    heartbeat_watch_timer = timer.Timer(15000000, no_heartbeat_callback)
    heartbeat_watch_timer.start()

def no_heartbeat_callback():
    print 'server could be down, not received heartbeat in the last 15s'

    start_heartbeat_watch()

def heartbeat_callback(message, channel):
    print 'server is healty, received its heartbeat (' + message['params'] + ')'

    heartbeat_watch_timer.stop()
    
    start_heartbeat_watch()

pubnub.subscribe(
    channels = 'status',
    callback = heartbeat_callback
)

start_heartbeat_watch()

send_message(start_message)

time.sleep(10)

send_message({
    'resource': 'water_pump',
    'operation': 'set_speed',
    'params': 100
})

time.sleep(15)

send_message(stop_message)


while True:
    time.sleep(5000)
