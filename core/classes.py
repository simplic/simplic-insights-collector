from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Self, TypeVar

"""
A version (major.minor.patch+extra)
"""
@dataclass
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    extra: str | None = None

class Status(str, Enum):
    UNKNOWN = 'unknown'
    """The status of a sensor is not known"""

    TIMEOUT = 'timeout'
    """Reading the sensor timed out"""

    ERROR = 'error'
    """An error occured while reading the sensor"""

    UNSET = 'unset'
    """There are no rules that specify the status of the sensor"""

    UNHEALTHY = 'unhealthy'
    DEGRADED = 'degraded'
    HEALTHY = 'healthy'

class Measurement:
    @classmethod
    def now(cls, status: Status, data: Any = None, error: str | None = None, trace: list[str] | None = None) -> Self:
        return cls(datetime.now(), status, data, error, trace)

    def __init__(self, time: datetime, status: Status, data: Any = None, error: str | None = None, trace: list[str] | None = None) -> None:
        self.time = time
        self.status = status
        self.data = data
        self.error = error
        self.trace = trace

    def toJSON(self) -> dict[str, Any]:
        return {
            'time': str(self.time),
            'status': self.status.value,
            'data': self.data,
            'error': {
                'message': self.error,
                'trace': self.trace,
            } if self.error else None,
        }

class SettingsBase:
    """
    The base class for all sensor settings
    """

    @classmethod
    def schema(cls) -> Any:
        """
        Get JSON schema for these settings.
        This might be used for UI later

        :returns: JSON schema
        """
        return {}

    @classmethod
    def deserialize(cls, json: Any) -> Self:
        """
        Load settings from the config file

        :param json: Deserialized contents of the the "settings" key in settings.json

        :returns: Deserialized settings
        """
        return cls()

    def serialize(self) -> Any:
        """
        Serialize settings to json

        :returns: JSON value
        """
        return None

_Settings = TypeVar('_Settings', bound=SettingsBase)
class SensorBase(ABC, Generic[_Settings]):
    """
    The base class for all sensors
    """

    @abstractmethod
    def __init__(self, settings: _Settings) -> None:
        """
        Create a sensor with settings.
        Initialization should be done in start()
        """

    def start(self) -> None:
        """
        Prepare for measurement.
        This is called once
        """

    @abstractmethod
    def measure(self) -> Measurement:
        """
        Perform a measurement

        :returns: Sensor data
        """

@dataclass
class SensorDef:
   id: str
   sensor: type[SensorBase]
   settings: type[SettingsBase]
   batch: bool = True
   """Whether previous sensor data should be batched or ignored"""
