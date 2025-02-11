from core import Measurement, SensorBase, SensorDef, SettingsBase, Status, cast, jsonget
from datetime import datetime, timezone
import os
from typing import Any, Self

from core.classes import Metric
from core.util import format_time

class ExistsSettings(SettingsBase):
    @classmethod
    def deserialize(cls, json: Any) -> Self:
        json = cast('settings', json, dict)
        path = jsonget(json, 'path', str)
        file = jsonget(json, 'file', bool, default=False)
        dir = jsonget(json, 'dir', bool, default=False)
        return cls(path, file, dir)

    def __init__(self, path: str, file: bool, dir: bool) -> None:
        self.path = path
        self.file = file
        self.dir = dir

class ExistsSensor(SensorBase[ExistsSettings]):
    def __init__(self, settings: ExistsSettings) -> None:
        self.settings = settings

    def measure(self) -> Measurement:
        metrics = []
        status = Status.UNHEALTHY

        if self.settings.file:
            file_exists = os.path.isfile(self.settings.path)
            metrics.append(Metric('is_file', 'bool', file_exists))

            if file_exists:
                status = Status.HEALTHY
        
        if self.settings.dir:
            dir_exists = os.path.isdir(self.settings.path)
            metrics.append(Metric('is_dir', 'bool', dir_exists))
            
            if dir_exists:
                status = Status.HEALTHY

        return Measurement.now(status, metrics)

class AgeSettings(SettingsBase):
    @classmethod
    def deserialize(cls, json: Any) -> Self:
        json = cast('settings', json, dict)
        path = jsonget(json, 'path', str)
        unhealthy = datetime.fromisoformat(jsonget(json, 'unhealthy', str))
        degraded = datetime.fromisoformat(jsonget(json, 'degraded', str))

        return cls(path, unhealthy, degraded)

    def __init__(self, path: str, unhealthy: datetime, degraded: datetime) -> None:
        self.path = path
        self.unhealthy = unhealthy
        self.degraded = degraded

class AgeSensor(SensorBase[AgeSettings]):
    def __init__(self, settings: AgeSettings) -> None:
        self.settings = settings

    def measure(self) -> Measurement:
        if os.path.exists(self.settings.path):
            age = datetime.fromtimestamp(os.path.getmtime(self.settings.path), tz=timezone.utc)
            
            metrics = [
                Metric('age', 'time', format_time(age))
            ]

            if age < self.settings.unhealthy:
                status = Status.UNHEALTHY
            elif age < self.settings.degraded:
                status = Status.DEGRADED
            else:
                status = Status.HEALTHY
            
            return Measurement.now(status, metrics)
        
        return Measurement.now(Status.ERROR, error='path does not exist')

SENSORS = [
    SensorDef('age', AgeSensor, AgeSettings),
    SensorDef('exists', ExistsSensor, ExistsSettings),
]
