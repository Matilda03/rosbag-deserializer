# rosbag-deserializer

This project contains Python scripts for deserializing ROS (Robot Operating System) bag files and working with MQTT messaging for sensor data processing and playback.

## Project Structure

```
rosbag-deserializer/
├── Data/                    # Data processing and parsing modules
│   ├── ROSDeserializer.py   # Core ROS bag deserialization functionality
│   ├── ROSMessageParser.py  # ROS message parsing utilities
│   ├── SensorMessagesParser.py # Sensor-specific message parsing
│   ├── metadata.yaml        # Configuration metadata
│   ├── sample-rosbag_0.db3  # Sample ROS bag database file
│   └── sensor_data_buildings.xlsx # Excel data file with sensor information
├── Scripts/                 # Main execution scripts
│   ├── ExcelToMQTT.py      # Excel to MQTT data conversion
│   ├── MQTTMessagePlayback.py # MQTT message playback functionality
│   └── details.csv         # Configuration details
├── Dockerfile              # Docker container configuration
└── docker-compose.yml      # Docker Compose orchestration
```

## Scripts Description

### Data Processing Modules

- **`ROSDeserializer.py`**: Core module for deserializing ROS bag files from SQLite database format. Handles the conversion of ROS bag data into a more accessible format for processing.

- **`ROSMessageParser.py`**: Utility module for parsing ROS messages. Provides functionality to extract and interpret different types of ROS message formats.

- **`SensorMessagesParser.py`**: Specialized parser for sensor messages. Handles the extraction and processing of sensor-specific data from ROS messages.

### Execution Scripts

- **`ExcelToMQTT.py`**: Converts sensor data from Excel spreadsheets to MQTT messages. This script reads sensor data from Excel files and publishes it to MQTT topics for real-time data streaming.

- **`MQTTMessagePlayback.py`**: Provides MQTT message playback functionality. This script can replay previously recorded MQTT messages, useful for testing and simulation scenarios.

## Data Files

- **`sample-rosbag_0.db3`**: Sample ROS bag file in SQLite database format containing recorded robot/sensor data
- **`sensor_data_buildings.xlsx`**: Excel spreadsheet containing sensor data from buildings
- **`metadata.yaml`**: Configuration file with metadata for the processing pipeline
- **`details.csv`**: Configuration details for the scripts

## Docker Support

The project includes Docker configuration files:
- **`Dockerfile`**: Container definition for the application
- **`docker-compose.yml`**: Multi-container orchestration setup

## Requirements

- Python 3.11.9
- SQLite support for ROS bag processing
- MQTT client libraries
- Excel file processing capabilities

## Usage

1. **ROS Bag Processing**: Use the modules in the `Data/` directory to deserialize and parse ROS bag files
2. **Excel to MQTT**: Run `ExcelToMQTT.py` to convert Excel sensor data to MQTT messages
3. **Message Playback**: Use `MQTTMessagePlayback.py` to replay MQTT messages for testing or simulation

## Docker Deployment

The project can be containerized using the provided Docker configuration:

```shell script
docker-compose up
```
