from threading import Thread
import eventlet
import paho.mqtt.client as mqtt
import rethinkdb as r
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

eventlet.monkey_patch()
app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')


def on_connect(mqttc, obj, flags, rc):
    print("rc: "+str(rc))


def on_message(mqttc, obj, msg):
    # print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload.decode('ascii')))
    topic = msg.topic
    data = msg.payload.decode('ascii')
    dt = {'topic': topic}
    di = {'data': data}
    socketio.emit('server_topic',
                      {'data': dt['topic']}, namespace='/test')
    socketio.emit('server_data',
                      {'data': di['data']}, namespace='/test')


def on_publish(mqttc, obj, mid):
    pass
    #print("mid: "+str(mid))


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
mqttc.subscribe("server", 0)

conn = r.connect(host='localhost', port=28015, db='poolpi')
conn1 = r.connect(host='localhost', port=28015, db='poolpi')
thread0 = None


# when a change in the database is detected, send data to webpade
def background_thread():
    feed = r.table('orp').union(r.table('ph').union(r.table('flow').union(r.table('temp')))).changes().run(conn)
    for change in feed:
        di = change
        if 'orp' in di['new_val']:
            socketio.emit('orp',
                      {'data': di['new_val']['orp']}, namespace='/test')
            socketio.emit('orp_time',
                      {'data': di['new_val']['orp_time']}, namespace='/test')
        elif 'ph' in di['new_val']:
            socketio.emit('ph',
                      {'data': di['new_val']['ph']}, namespace='/test')
            socketio.emit('ph_time',
                      {'data': di['new_val']['ph_time']}, namespace='/test')
        elif 'flow' in di['new_val']:
            socketio.emit('flow',
                      {'data': di['new_val']['flow']}, namespace='/test')
            socketio.emit('flow_time',
                      {'data': di['new_val']['flow_time']}, namespace='/test')
        elif 'temp' in di['new_val']:
            socketio.emit('temp',
                      {'data': di['new_val']['temp']}, namespace='/test')
            socketio.emit('temp_time',
                      {'data': di['new_val']['temp_time']}, namespace='/test')
        else:
            pass


# index page that displays real time data
@app.route('/')
def index():
    global thread0
    if thread0 is None:
        thread0 = Thread(target=background_thread)
        thread0.start()
    return render_template('index.html')


# when data is sent from webpage to background process
@socketio.on('my event', namespace='/test')
def test_message(message):
    user_com = message['data']
    print(user_com)
    mqttc.publish('controller', user_com, 1)
    # di = {}
    # di['data'] = str(message['data'])
    # di['time'] = r.now().to_iso8601()
    # r.table('user_input_data').insert(di).run(conn1)


@socketio.on('connect', namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    pass
    #print('Client disconnected')

if __name__ == '__main__':
    mqttc.loop_start()
    socketio.run(app, debug=True)
