# simplic-insights-collector
Simplic insights host/collector



## Usage

1. Create `settings.json`  
   An example is given as `settings.example.json`
2. Set URL, API key and upload interval
3. Configure the sensors you need
4. Run `python launch.py`



## Creating a sensor package

1. Give your package a unique id
2. Create a new folder `sensors/<id>/`
3. Create `__init__.py` and `manifest.json`
4. Add id, version, name, description and dependencies to `manifest.json`
5. For each sensor:
   - Create and implement a Settings class derived from SettingsBase
   - Create and implement a Sensor class derived from SensorBase
6. Register all sensors in your `__init__.py` like this:  
    ```py
    SENSORS = [
      SensorDef('my-sensor', MySensor, MySettings),
    ]
    ```



## Structure

`settings.json`  
- API settings
- Upload settings
  - `min_interval`: Measurements will be batched and sent in this interval
  - `max_interval`: How long to wait for sensor data until sending an empty packet  
                    This is is useful to notify the server that this Host still runs,
                    even if there is no sensor data available
- Sensors:
  - `type`: ID of the sensor class, as `package:identifier`
  - `name`: Display name
  - `interval`: Update interval

`launcher.py`  
- The main entry point.
- Copies used sensor packages
- Installs required dependencies.

`main.py`  
- Loads the settings file
- Measures sensor values
- Uploads values to an API.

`core/`  
Core library used by sensors

`sensors/`  
Built-in sensors

`sensors/<pkg>/manifest.json`  
Used by the loader to install dependencies  
Can be used later for an online index of sensors

`sensors/<pkg>/__init__.py`  
Entry point for a sensor package

`schemas/`  
JSON schemas for the configuration files



## Sensors

The following section contains the available sensor types

### Package `system`
- CPU usage  
  - Measure CPU usage
- RAM usage
  - Measure RAM and Swap usage

### Disk usage

Checks available disk usage

### Package `rabbitmq`

Checks whether a RabbitMQ server is available and accepts connections

### Redis

Checks whether a Redis server is available and accepts connections

### Sybase

Checks whether a sybase sql anywhere server is available and accepts connections

### MSSQL

Checks whether a mssql server is available and accepts connections

### Service is running

Checks whether a given service is running

### Process

Checks whether a process is running

### Directory file age

Checks, whether files in a directory are not older than x (seconds?)

### Directory exists

Checks whether a directory exists

### File eixsts

Checks whether a file exists

### Http

Checks whether an http(s) endpoint is available, by sending a HEAD-Request



