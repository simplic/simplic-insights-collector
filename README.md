# simplic-insights-collector
Simplic insights host/collector



## Usage

1. Create `settings.json`  
   An example is given as `settings.example.json`
2. Set URL, API key and upload interval
3. Configure the sensors you need
4. Run `python launcher.py`



## Creating a sensor package

[Example package](https://github.com/simplic/simplic-insights-package-example)

1. Give your package a unique id
2. Create a new folder somewhere
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

## Use the sensor package
If you want to test the package before publishing to GitHub, you can use it locally by adding this to your `settings.json`
```json
"packages": [
    {
        "type": "folder",
        "path": "/path/to/folder"
    }
]
```
And set the path to the folder containing `settings.json` and `sensors/`


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

`schemas/`  
JSON schemas for the configuration files



## Sensors

Links to sensor packages

### Package `example`
Example sensor package  
https://github.com/simplic/simplic-insights-package-example

### Package `system`
Various system-related sensors (cpu, ram, ...)  
https://github.com/simplic/simplic-insights-package-example

### Package `rabbitmq`
Detect if a RabbitMQ server is available  
https://github.com/simplic/simplic-insights-package-example


### Not implemented yet:

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

### Http
Checks whether an http(s) endpoint is available, by sending a HEAD-Request
