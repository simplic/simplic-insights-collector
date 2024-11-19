from core import Measurement, SensorBase, SensorDef, SettingsBase, Status, cast
import psutil
from typing import Any, Self

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

        data = {
            'percent': percent,
            'freq': {'current': freq.current, 'min': freq.min, 'max': freq.max}
        } if self.settings.extra else {}

        if unhealthy:
            return Measurement.now(Status.UNHEALTHY, data)
        if degraded:
            return Measurement.now(Status.DEGRADED, data)
        return Measurement.now(Status.HEALTHY, data)



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

        data = {
            'mem': {'total': mem.total, 'available': mem.available},
            'swap': {'total': swap.total, 'free': swap.free}
        } if self.settings.extra else {}

        if unhealthy:
            return Measurement.now(Status.UNHEALTHY, data)
        if warning:
            return Measurement.now(Status.DEGRADED, data)
        return Measurement.now(Status.HEALTHY, data)



SENSORS = [
    SensorDef('ram', RAMUsageSensor, RAMUsageSettings),
    SensorDef('cpu', CPUUSageSensor, CPUUsageSettings),
]
