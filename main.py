from collections import deque
from dataclasses import dataclass
import importlib
import json
from queue import Empty, Queue
import sys
from threading import Event, Thread
import time
import traceback
from typing import Any

import requests

from core import Measurement, SensorBase, SensorDef, Status, cast, parse_interval

@dataclass
class SensorConfig:
    type: str
    name: str
    data: str
    secs: float


def measure_loop(sensor: SensorBase, index: int, queue: Queue[tuple[int, Measurement]], secs: float, stop: Event):
    # TODO: More accurate timing, timeout if a sensor takes too long

    try:
        sensor.start()
    except Exception as e:
        print(f'ERR: Sensor failed to start: {e}')
        queue.put((index, Measurement.now(Status.ERROR, error=str(e))))
        # The sensor is in an invalid state
        return
    
    while not stop.wait(secs):
        try:
            result = sensor.measure()
        except Exception as e:
            trace = traceback.format_tb(e.__traceback__) if debug else None
            result = Measurement.now(Status.ERROR, error=str(e), trace=trace)

        queue.put((index, result))

def upload_loop(url: str, host: str, token: str, configs: list[SensorConfig], queue: Queue[tuple[int, Measurement]], min_secs: float, max_secs: float, backlog: int, stop: Event):
    # TODO: More accurate timing

    last = time.time()
    print(min_secs)
    not_send = dict[int, deque[Measurement]]()
    while not stop.wait(min_secs):
        # Batch measurements
        while True:
            try:
                index, item = queue.get_nowait()
                if index not in not_send:
                    not_send[index] = deque()
                # Remove old measurements
                if len(not_send[index]) >= backlog:
                    del not_send[index][0]
                not_send[index].append(item)
            except Empty:
                break

        # Convert to JSON-serializable
        sdata = list[dict[str, Any]]()
        for index, values in not_send.items():
            config = configs[index]
            sdata.append({'type': config.type, 'name': config.name, 'data': list(map(Measurement.toJSON, values))})

        # Upload data
        if len(sdata) > 0 or time.time() - last > max_secs:
            headers = {'Authorization': 'Bearer ' + token}
            data = {'host': host, 'sensors': sdata}
            try:
                if debug:
                    print('sending', json.dumps(data, indent='  '))
                requests.post(url, headers=headers, json=data)
                last = time.time()
                not_send = {}
            except Exception as e:
                print(f'ERR: Upload failed: {e}')

# This should be set by launcher.py
settings_file = sys.argv[1]
debug = sys.argv[2] == 'debug'

with open(settings_file, 'rt') as f:
    settings = json.load(f)

url = cast('url', settings['url'], str)
host = cast('host', settings['host'], str)
token = cast('token', settings['token'], str)
upload = cast('upload', settings['upload'], dict)
min_upload_secs = parse_interval(cast('min_interval', upload['min_interval'], str))
max_upload_secs = parse_interval(cast('max_interval', upload['max_interval'], str))
max_backlog = cast('max_backglog', upload['max_backlog'], int)

pkgs = set[str]()
configs = list[SensorConfig]()
for sensor in settings['sensors']:
    type = cast('type', sensor['type'], str)
    name = cast('name', sensor['name'], str)
    data = sensor['settings']

    pkg, id = type.split(':')
    pkgs.add(pkg)
    secs = parse_interval(cast('interval', sensor['interval'], str))
    if secs < 0.05:
        raise ValueError('Interval must be >= 50ms')

    configs.append(SensorConfig(type, name, data, secs))

sensors = dict[str, SensorDef]()
for pkg in pkgs:
    print('Loading package', pkg)
    mod = importlib.import_module('sensors.' + pkg)
    mod_sensors = cast('SENSORS', mod.SENSORS, list)
    for sensor in mod_sensors:
        sensor = cast('SENSORS[i]', sensor, SensorDef)
        sensors[pkg + ':' + sensor.id] = sensor

print('Loaded', len(sensors), 'sensor(s) from', len(pkgs), 'package(s)')

print('Creating', len(configs), 'sensors')
insts = list[SensorBase]()
try:
    for config in configs:
        sensor = sensors[config.type]
        settings = sensor.settings.deserialize(config.data)
        insts.append(sensor.sensor(settings))
except Exception as e:
    print('Sensors failed to start, aborting')
    raise e

queue = Queue[tuple[int, Measurement]]()
threads = list[Thread]()
event_stop = Event()
for index, inst in enumerate(insts):
    thread = Thread(target=measure_loop, args=(inst, index, queue, configs[index].secs, event_stop))
    thread.start()

thread = Thread(target=upload_loop, args=(url, host, token, configs, queue, min_upload_secs, max_upload_secs, max_backlog, event_stop))
thread.start()

print('Running')

input('Press Enter to stop\n')

event_stop.set()
print('Waiting for threads to join')
thread.join()
for thread in threads:
    thread.join()

print('Stopped')
