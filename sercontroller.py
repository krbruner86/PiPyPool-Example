import paho.mqtt.client as mqtt
import rethinkdb as r
from ser_flow1 import flow_query
from ser_orp import orp_query
from ser_ph1 import ph_query
from temp1 import temp_query

conn1 = r.connect(db='poolpi').repl()
rec_msg = None
temp = ''


# set up mqtt communications
def on_connect(mqttc, obj, flags, rc):
    print("rc: "+str(rc))


def on_message(mqttc, obj, msg):
    global temp
    global rec_msg
    if msg.topic == 'temp_calibrate':
        temp = str(msg.payload)
    else:
        rec_msg = str(msg.payload.decode('ascii'))
    # print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload.decode('ascii')))


def on_publish(mqttc, obj, mid):
    print("mid: "+str(mid))


def on_log(mqttc, obj, level, string):
    print(string)


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

mqttc = mqtt.Client()
mqttc.on_message = on_message
mqttc.on_publish = on_publish
mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.connect("localhost", 1883, 60)
mqttc.subscribe([("controller", 0), ('temp_calibrate', 0)])


# main program that routes all messages to the corresponding circuit
def main():
    last_correct = 0
    ph_command = 'r'
    orp_command = 'r'
    flow_command = 'r'
    temp_command = ''
    global rec_msg
    global temp
    while not rec_msg:
        print(ph_query(ph_command))
        print(orp_query(orp_command))
        print(flow_query(flow_command))
        last_correct += 1
        if last_correct >= 25:
            print(temp_query(temp_command))
            # temp = r.table('temp').order_by(r.desc('temp_time')).limit(1).run(conn1)
            # di = temp[0]
            # ph_query('t,' + str(di['temp']))
            ph_query('t,' + temp)
            last_correct = 0
            continue
        while rec_msg:
            while rec_msg[0] == '0':
                if rec_msg[1:] == 'off':
                    mqttc.publish('ph_prog', 'off', 0)
                    ph_command = 'off'
                    rec_msg = '4'
                    pass
                elif rec_msg[1:] == 'auto':
                    mqttc.publish('ph_prog', 'auto', 0)
                    ph_command = 'r'
                    rec_msg = '4'
                    pass
                elif rec_msg[1:] == 'manual':
                    mqttc.publish('ph_prog', 'manual', 0)
                    ph_command = 'r'
                    rec_msg = '4'
                    pass
                else:
                    print('sending message')
                    print(ph_query(rec_msg[1:]))
                    rec_msg = '4'
                    pass
            while rec_msg[0] == '1':
                if rec_msg[1:] == 'off':
                    print(orp_query('c,0'))
                    orp_command = 'off'
                    rec_msg = '4'
                    pass
                elif rec_msg[1:] == 'auto':
                    print(orp_query('c,1'))
                    orp_command = ''
                    rec_msg = '4'
                    pass
                else:
                    print('sending message')
                    print(orp_query(rec_msg[1:]))
                    rec_msg = '4'
                    pass
            while rec_msg[0] == '2':
                if rec_msg[1:] == 'off':
                    print(flow_query('c,0'))
                    flow_command = 'off'
                    rec_msg = '4'
                    pass
                elif rec_msg[1:] == 'auto':
                    print(flow_query('c,1'))
                    flow_command = ''
                    rec_msg = '4'
                    pass
                else:
                    print('sending message')
                    print(flow_query(rec_msg[1:]))
                    rec_msg = '4'
                    pass
            while rec_msg[0] == '3':
                if rec_msg[1:] == 'off':
                    print(temp_query('c,0'))
                    temp_command = 'off'
                    rec_msg = '4'
                    pass
                elif rec_msg[1:] == 'auto':
                    print(temp_query('c,1'))
                    temp_command = ''
                    rec_msg = '4'
                    pass
                else:
                    print('sending message')
                    print(temp_query(rec_msg[1:]))
                    rec_msg = '4'
                    pass
            while rec_msg[0] == '4':
                rec_msg = None
                break
            break
mqttc.loop_start()
main()