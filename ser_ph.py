import io
import sys
import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import rethinkdb as r
import serial


# set up mqtt communications
def on_publish(mqttc, obj, mid):
    print("mid: "+str(mid))


def on_connect(mqttc, obj, flags, rc):
    print("rc: "+str(rc))


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))


def on_message(mqttc, obj, msg):
    print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload.decode('ascii')))

mqttc = mqtt.Client()
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_message = on_message
mqttc.on_subscribe = on_subscribe
mqttc.connect("localhost", 1883, 60)
mqttc.subscribe("ph", 0)
mqttc.loop_start()

# commands that are accepted
lst = ['?', 'L', 'C', 'T', 'N', 'R']
ph_list = []


# data sent to pH circuit
def ph_query(command):
    global ph_list
    global lst

    GPIO.setmode(GPIO.BCM)

    # change channel on serial communications board
    S0_pin = 17
    S1_pin = 23
    GPIO.setup(S0_pin, GPIO.OUT)  # S0
    GPIO.setup(S1_pin, GPIO.OUT)  # S1
    GPIO.output(S0_pin, GPIO.LOW)
    GPIO.output(S1_pin, GPIO.LOW)

    usbport = '/dev/ttyAMA0'
    ser = serial.Serial(usbport, 9600, timeout=0)
    sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser), encoding='ascii', newline='\r', line_buffering=True)

    di = {}

    # handle the different commands
    conn1 = r.connect(db='poolpi').repl()
    if command == 'r':
        try:
            command += '\r'
            sio.write(command)
            while True:
                try:
                    time.sleep(.1)
                    line = sio.readline()
                    lg = len(line)
                    if lg > 0:
                        if line == '*ER\r':
                            sio.write(command)
                            sio.flush()
                            continue
                        else:
                            float_ph_reading = float(line)
                            rounded_result = round(float_ph_reading, 1)
                            # print('raw pH: %r' % (rounded_result))
                            try:
                                if len(ph_list) == 10:
                                    del ph_list[0]
                                    ph_list.append(rounded_result)
                                    ph_sum = sum(ph_list)
                                    ph_avg = ph_sum / 10
                                    rounded_ph_avg = round(ph_avg, 1)
                                else:
                                    ph_list.append(rounded_result)
                                    ph_list_length = len(ph_list)
                                    ph_sum = sum(ph_list)
                                    ph_avg = ph_sum / ph_list_length
                                    rounded_ph_avg = round(ph_avg, 1)
                            except ValueError:
                                GPIO.cleanup()
                                return "Value Error"
                            try:
                                # mqttc.publish('ph_sensor',char_line[:-1], 0)
                                di['ph'] = rounded_ph_avg
                                di['ph_time'] = r.now().to_iso8601()
                                r.table('ph').insert(di).run(conn1)
                                GPIO.cleanup()
                                return 'pH: %r' % (rounded_ph_avg)
                            except:
                                print(sys.exc_info())
                                GPIO.cleanup()
                                return "Error writing to database"
                except:
                    print(sys.exc_info())
        except KeyboardInterrupt: GPIO.cleanup()
    elif command == 'off':
        return
    else:
        try:
            retry = 0
            print('sending command...')
            command += '\r'
            sio.write(command)
            try:
                while True:
                    time.sleep(.1)
                    line = sio.readline()
                    lg = len(line)
                    if lg > 0:
                        if line[0] in lst:
                            print(line)
                            mqttc.publish('server', line, 0)
                            return line
                        elif line == '*ER\r':
                            sio.write(command)
                            sio.flush()
                            mqttc.publish('server', 'error, trying again', 0)
                            retry += 1
                            continue
                        elif line == '*OK\r':
                            print(line)
                            mqttc.publish('server', line, 0)
                            return line
                        elif retry >= 10:
                            mqttc.publish('server', 'error, please try again', 0)
                            return
                        else:
                            retry += 1
                            print('hello there')
                            continue
            except:
                return
        except KeyboardInterrupt: GPIO.cleanup()


if __name__ == '__main__':
    while True:
        print(ph_query(''))
        time.sleep(1)
