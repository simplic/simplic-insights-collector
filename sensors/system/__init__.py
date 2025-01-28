from core import Measurement, SensorBase, SensorDef, SettingsBase, Status, cast
import psutil
from typing import Any, Self

from core.classes import Metric

class CPUUsageSettings(SettingsBase):
    @classmethod
    def deserialize(cls, json: Any) -> Self:
        json = cast('settings', json, dict)
        unhealthy = cast('unhealthy', json['unhealthy'], str)
        degraded = cast('degraded', json['degraded'], str)
        extra = cast('extra', json['extra'], bool)
        return cls(unhealthy, degraded, extra)
    
    def __init__(self, unhealthy: str, degraded: str, extra: bool) -> None:
        self.unhealthy = unhealthy
        self.degraded = degraded
        self.extra = extra

class CPUUSageSensor(SensorBase[CPUUsageSettings]):
    def __init__(self, settings: CPUUsageSettings) -> None:
        self.settings = settings

    def measure(self) -> Measurement:
        percent = psutil.cpu_percent()
        freq = psutil.cpu_freq()

        vars = { 'percent': percent, 'freq': freq }
        xunhealthy = eval(self.settings.unhealthy, vars)
        xdegraded = eval(self.settings.degraded, vars)
        unhealthy = cast('unhealthy()', xunhealthy, bool)
        degraded = cast('degraded()', xdegraded, bool)

        metrics = [
            Metric('percent', '%', percent),
            Metric('freq.cur', 'Hz', freq.current),
            Metric('freq.min', 'Hz', freq.min),
            Metric('freq.max', 'Hz', freq.max),
         ] if self.settings.extra else []

        if unhealthy:
            return Measurement.now(Status.UNHEALTHY, metrics)
        if degraded:
            return Measurement.now(Status.DEGRADED, metrics)
        return Measurement.now(Status.HEALTHY, metrics)



class RAMUsageSettings(SettingsBase):
    @classmethod
    def deserialize(cls, json: Any) -> Self:
        json = cast('settings', json, dict)
        unhealthy = cast('unhealthy', json['unhealthy'], str)
        degraded = cast('degraded', json['degraded'], str)
        extra = cast('extra', json['extra'], bool)
        return cls(unhealthy, degraded, extra)

    def __init__(self, unhealthy: str, degraded: str, extra: bool) -> None:
        self.unhealthy = unhealthy
        self.degraded = degraded
        self.extra = extra

class RAMUsageSensor(SensorBase[RAMUsageSettings]):
    def __init__(self, settings: RAMUsageSettings) -> None:
        self.settings = settings

    def measure(self) -> Measurement:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        vars = {'mem': mem, 'swap': swap}
        xunhealthy = eval(self.settings.unhealthy, vars)
        xdegraded = eval(self.settings.degraded, vars)
        unhealthy = cast('unhealthy()', xunhealthy, bool)
        warning = cast('warning()', xdegraded, bool)

        metrics = [
            Metric('mem.total', 'B', mem.total),
            Metric('mem.free', 'B', mem.available),
            Metric('swap.total', 'B', swap.total),
            Metric('swap.free', 'B', swap.free),
        ] if self.settings.extra else []

        if unhealthy:
            return Measurement.now(Status.UNHEALTHY, metrics)
        if warning:
            return Measurement.now(Status.DEGRADED, metrics)
        return Measurement.now(Status.HEALTHY, metrics)



class DiskUsageSettings(SettingsBase):
    @classmethod
    def deserialize(cls, json: Any) -> Self:
        json = cast('settings', json, dict)
        path = cast('path', json['path'], str)
        unhealthy = cast('unhealthy', json['unhealthy'], str)
        degraded = cast('degraded', json['degraded'], str)
        extra = cast('extra', json['extra'], bool)
        return cls(path, unhealthy, degraded, extra)

    def __init__(self, path: str, unhealthy: str, degraded: str, extra: bool) -> None:
        self.path = path
        self.unhealthy = unhealthy
        self.degraded = degraded
        self.extra = extra

class DiskUsageSensor(SensorBase[DiskUsageSettings]):
    def __init__(self, settings: DiskUsageSettings) -> None:
        self.settings = settings

    def measure(self) -> Measurement:
        disk = psutil.disk_usage(self.settings.path)

        vars = {'disk': disk}
        xunhealthy = eval(self.settings.unhealthy, vars)
        xdegraded = eval(self.settings.degraded, vars)
        unhealthy = cast('unhealthy()', xunhealthy, bool)
        degraded = cast('warning()', xdegraded, bool)

        metrics = [
            Metric('total', 'B', disk.total),
            Metric('free', 'B', disk.free),
        ] if self.settings.extra else []

        if unhealthy:
            return Measurement.now(Status.UNHEALTHY, metrics)
        if degraded:
            return Measurement.now(Status.DEGRADED, metrics)
        return Measurement.now(Status.HEALTHY, metrics)



SENSORS = [
    SensorDef('cpu', CPUUSageSensor, CPUUsageSettings),
    SensorDef('ram', RAMUsageSensor, RAMUsageSettings),
    SensorDef('disk', DiskUsageSensor, DiskUsageSettings),
]
