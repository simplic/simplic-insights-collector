from core import Measurement, SensorBase, SensorDef, SettingsBase, Status
import pika
import pika.exceptions
from typing import Self

from core.config import ReadValue

class RabbitMQSettings(SettingsBase):
    @classmethod
    def deserialize(cls, conf: ReadValue) -> Self:
        json = conf.as_dict()
        host = json['host'].as_str()
        port = json['port'].as_int(5672)
        vhost = json['vhost'].as_str('/')
        
        credentials = json['credentials'].as_dict(None)
        if credentials is not None:
            username = credentials['username'].as_str()
            password = credentials['password'].as_str()
            return cls(host, port, vhost, username, password)
        return cls(host, port, vhost)
    
    def __init__(self, host: str, port: int, vhost: str, username: str | None = None, password: str | None = None) -> None:
        self.host = host
        self.port = port
        self.vhost = vhost
        self.username = username
        self.password = password

class RabbitMQSensor(SensorBase[RabbitMQSettings]):
    def __init__(self, settings: RabbitMQSettings) -> None:
        if settings.username and settings.password:
            credentials = pika.PlainCredentials(settings.username, settings.password)
            self.parameters = pika.ConnectionParameters(settings.host, settings.port, settings.vhost, credentials)
        else:
            credentials = None
            self.parameters = pika.ConnectionParameters(settings.host, settings.port, settings.vhost)

    def measure(self) -> Measurement:
        try:
            pika.BlockingConnection(self.parameters)
            return Measurement.now(Status.HEALTHY)
        except pika.exceptions.AMQPConnectionError:
            return Measurement.now(Status.UNHEALTHY)



SENSORS = [
    SensorDef('running', RabbitMQSensor, RabbitMQSettings),
]
