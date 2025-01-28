from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
import os
import platform
from queue import Empty, Queue
import sys
from threading import Event, Thread
import time
import traceback
from uuid import UUID

import psutil
import requests

from core import Measurement, SensorBase, SensorDef, Status, cast, parse_interval
from core.util import eprint, format_time, get_ip_addr, jsonget

@dataclass
class HostConfig:
    uuid: UUID
    name: str
    url: str
    token: str
    min_secs: float
    max_secs: float
    max_backlog: int

@dataclass
class SensorConfig:
    uuid: UUID
    type: str
    name: str
    data: dict
    secs: float

def measure_loop(sensor: SensorBase, index: int, queue: Queue[tuple[int, Measurement]], secs: float, stop: Event):
    # TODO: More accurate timing, timeout if a sensor takes too long

    try:
        sensor.start()
    except Exception as e:
        eprint(f'ERR: Sensor failed to start: {e}')
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

def _send_measurement(url: str, token: str, config: SensorConfig, value: Measurement):
    metrics = []
    for metric in value.metrics:
        # Ignore metrics with invalid JSON
        try:
            metrics.append(metric.toJSON())
        except Exception as e:
            eprint(f'ERR: Serializing metric failed: {e}')

    headers = {'Authorization': 'Bearer ' + token}
    data = {
        'time': format_time(value.time),
        'sensorId': str(config.uuid),
        'message': config.name,
        'sensorHealthState': value.status,
        'metrics': metrics,
    }
    if value.error is not None:
        data['error'] = value.error
    if value.trace is not None:
        data['trace'] = value.trace
    
    try:
        if debug:
            print('sending to', repr(url), json.dumps(data, indent='  '))
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        eprint(f'ERR: Upload failed: {e}')

def _send_machine_data(url: str, token: str, name: str):
    boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)

    headers = {'Authorization': 'Bearer ' + token}
    data = {
        'ipAddress': get_ip_addr(),
        'hostName': name,
        'domain': os.environ.get('userdomain', None),
        'operatingSystem': platform.system(),
        'osVersion': platform.release(),
        'bootDateTime': format_time(boot_time),
    }

    try:
        if debug:
            print('sending to', repr(url), json.dumps(data, indent='  '))
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        print(f'ERR: Upload failed: {e}')

def upload_loop(host: HostConfig, configs: list[SensorConfig], queue: Queue[tuple[int, Measurement]], stop: Event):
    # TODO: More accurate timing

    url_machine = host.url + '/Host/machine-data/' + str(host.uuid)
    url_measure = host.url + '/Collector'

    _send_machine_data(url_machine, host.token, host.name)
    last = time.time()
    to_send = dict[int, deque[Measurement]]()
    while not stop.wait(host.min_secs):
        # Batch measurements
        while True:
            try:
                index, item = queue.get_nowait()
                if index not in to_send:
                    to_send[index] = deque()
                # Remove old measurements
                if len(to_send[index]) >= host.max_backlog:
                    del to_send[index][0]
                to_send[index].append(item)
            except Empty:
                break

        # Heartbeat
        if time.time() - last > host.max_secs:
            last = time.time()
            _send_machine_data(url_machine, host.token, host.name)
        
        # Upload data
        # TODO: Add batching to API
        for index, values in to_send.items():
            for value in values:
                _send_measurement(url_measure, host.token, configs[index], value)
        to_send = {}

# This should be set by launcher.py
settings_file = sys.argv[1]
debug = sys.argv[2] == 'debug'

with open(settings_file, 'rt') as f:
    settings = json.load(f)

# Load config file
uuid = UUID(jsonget(settings, 'uuid', str))
url = jsonget(settings, 'url', str)
name = jsonget(settings, 'name', str, default=platform.node())
token = jsonget(settings, 'token', str)
upload = jsonget(settings, 'upload', dict)
min_upload_secs = parse_interval(jsonget(upload, 'min_interval', str))
max_upload_secs = parse_interval(jsonget(upload, 'max_interval', str))
max_backlog = jsonget(upload, 'max_backlog', int)

host = HostConfig(uuid, name, url, token, min_upload_secs, max_upload_secs, max_backlog)


# Load sensor settings
pkgs = set[str]()
configs = list[SensorConfig]()
for sensor in settings['sensors']:
    uuid = UUID(jsonget(sensor, 'uuid', str))
    type = jsonget(sensor, 'type', str)
    name = jsonget(sensor, 'name', str)
    data = jsonget(sensor, 'settings', dict)

    pkg, id = type.split(':')
    pkgs.add(pkg)
    secs = parse_interval(jsonget(sensor, 'interval', str))
    if secs < 0.05:
        raise ValueError('Interval must be >= 50ms')

    configs.append(SensorConfig(uuid, type, name, data, secs))

# Load sensor python scripts
sensors = dict[str, SensorDef]()
for pkg in pkgs:
    print('Loading package', pkg)
    mod = importlib.import_module('sensors.' + pkg)
    mod_sensors = cast('SENSORS', mod.SENSORS, list)
    for sensor in mod_sensors:
        sensor = cast('SENSORS[i]', sensor, SensorDef)
        sensors[pkg + ':' + sensor.id] = sensor

print('Loaded', len(sensors), 'sensor(s) from', len(pkgs), 'package(s)')

# Instantiate sensor scripts
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

# Run measuring loop on a different thread
queue = Queue[tuple[int, Measurement]]()
threads = list[Thread]()
event_stop = Event()
for index, inst in enumerate(insts):
    thread = Thread(target=measure_loop, args=(inst, index, queue, configs[index].secs, event_stop))
    thread.start()

thread = Thread(target=upload_loop, args=(host, configs, queue, event_stop))
thread.start()

print('Running')

input('Press Enter to stop\n')

event_stop.set()
print('Waiting for threads to join')
thread.join()
for thread in threads:
    thread.join()

print('Stopped')
