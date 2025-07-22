#!/usr/bin/env python3
import pandas as pd
import ssl
import paho.mqtt.client as mqtt
import socket
import sys
import os
import argparse
import time
from datetime import datetime

# MQTT Configuration
BROKER = "mqtt.dtlab.eaisi.tue.nl"
PORT = 8883
USERNAME = "matilda"  # Replace with actual username if needed
PASSWORD = "cedalo1234"  # Replace with actual password if needed
TLS_CA_CERTS = None  # Set to path of CA cert if needed, else None

# Topic prefixes for different sensor types
TOPIC_PREFIXES = {
    "temperature": "test/Temperature/addedFromClient1",
    "occupancy": "test/Occupancy/addedFromClient1",
    "humidity": "test/Humidity/addedFromClient1"
}

# Mapping of sensor type to data column name
SENSOR_VALUE_COLUMNS = {
    "temperature": "temperature",
    "occupancy": "occupancy",
    "humidity": "humidity"
}

def parse_args():
    parser = argparse.ArgumentParser(description="Publish sensor data from Excel to MQTT.")
    parser.add_argument(
        "--excel_file",
        type=str,
        default="../Data/sensor_data_buildings.xlsx",
        help="Path to the Excel file containing sensor data."
    )
    parser.add_argument(
        "--sensors",
        type=str,
        default="",
        help="Comma-separated list of sensor names (sheet names) to send. If omitted, all sensors are sent."
    )
    parser.add_argument(
        "--speedup",
        type=float,
        default=1.0,
        help="Speed up factor for time intervals (e.g., 2.0 = twice as fast)."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop the messages after reaching the end of the data."
    )
    return parser.parse_args()

def get_excel_sheets(excel_file):
    """Get all sheet names from the Excel file."""
    try:
        xls = pd.ExcelFile(excel_file)
        return xls.sheet_names
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        sys.exit(1)

def prompt_for_sensors(sheet_names):
    """Interactively prompt for sensor selection."""
    print("Available sensors (sheet names):")
    for idx, name in enumerate(sheet_names, 1):
        print(f"{idx}: {name}")
    print("Enter the numbers of the sensors you want to use, separated by commas (e.g., 1,3,5), or press Enter to select all:")
    inp = input("> ").strip()
    if not inp:
        return sheet_names
    try:
        indices = [int(i) for i in inp.split(",") if i.strip()]
        selected = [sheet_names[i-1] for i in indices if 1 <= i <= len(sheet_names)]
        return selected
    except Exception:
        print("Invalid input, selecting all sensors.")
        return sheet_names

def prompt_for_speedup():
    """Interactively prompt for speedup factor."""
    print("Enter the speedup factor (e.g., 1.0 = real-time, 2.0 = twice as fast):")
    inp = input("> ").strip()
    if not inp:
        return 1.0
    try:
        val = float(inp)
        return max(0.1, val)
    except Exception:
        print("Invalid input, using 1.0.")
        return 1.0

def prompt_for_loop():
    """Interactively prompt whether to loop the data."""
    print("Do you want to loop the data after reaching the end? (y/n, default n):")
    inp = input("> ").strip().lower()
    return inp == "y"

def connect_mqtt():
    """Connect to MQTT broker and return the client."""
    try:
        client = mqtt.Client(protocol=mqtt.MQTTv311)
        client.username_pw_set(USERNAME, PASSWORD)
        client.tls_set(ca_certs=TLS_CA_CERTS, cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)

        # Test DNS resolution before connecting
        try:
            socket.gethostbyname(BROKER)
        except socket.gaierror:
            print(f"ERROR: Could not resolve broker address '{BROKER}'. Please check the broker address.")
            sys.exit(1)

        client.connect(BROKER, PORT)
        client.loop_start()
        return client
    except Exception as e:
        print(f"ERROR: Could not connect to MQTT broker: {e}")
        sys.exit(1)

def read_sensor_data(excel_file, sensor_names):
    """Read sensor data from the Excel file and return as dictionary."""
    sensor_data = {}

    for sensor_name in sensor_names:
        try:
            # Read the sheet with the sensor name
            df = pd.read_excel(excel_file, sheet_name=sensor_name)

            # Determine sensor type based on sensor name and available columns
            sensor_type = "temperature"  # Default
            for key in SENSOR_VALUE_COLUMNS.keys():
                if key in sensor_name.lower():
                    sensor_type = key
                    break

            # Check if the expected value column exists for this sensor type
            value_column = SENSOR_VALUE_COLUMNS[sensor_type]
            if value_column not in df.columns:
                print(f"Warning: Column '{value_column}' not found for sensor {sensor_name}. Looking for alternative columns...")
                # Try to guess the column
                for col in df.columns:
                    if value_column in col.lower():
                        value_column = col
                        break

            # Check that event_time column exists
            if 'event_time' not in df.columns:
                print(f"Warning: Required 'event_time' column not found in sensor {sensor_name}. Skipping.")
                continue

            # Extract required data with timestamp from event_time column only
            data = []
            for _, row in df.iterrows():
                try:
                    # Get timestamp from event_time column (ISO 8601 format)
                    if pd.isna(row['event_time']):
                        print(f"Warning: Missing event_time for a row in sensor {sensor_name}. Skipping row.")
                        continue

                    # Parse the event_time which is already in ISO 8601 format (e.g. 2025-03-08T21:34:57.000)
                    timestamp = pd.to_datetime(row['event_time'])

                    # Get the correct value based on sensor type
                    if value_column in row:
                        value = row[value_column]
                    else:
                        # Fallback to 'value' column if specific column not found
                        value = row.get('value', None)
                        if value is None:
                            print(f"Warning: No value found for row in sensor {sensor_name}. Skipping row.")
                            continue

                    data.append({
                        'timestamp': timestamp,
                        'value': value,
                        'sensor_type': sensor_type
                    })

                except Exception as e:
                    print(f"Error processing row for sensor {sensor_name}: {e}")
                    continue

            # Sort by timestamp
            data.sort(key=lambda x: x['timestamp'])

            sensor_data[sensor_name] = data
            print(f"Loaded {len(data)} data points for sensor {sensor_name} (type: {sensor_type})")

        except Exception as e:
            print(f"Error reading data for sensor {sensor_name}: {e}")

    return sensor_data

def publish_sensor_data(client, sensor_data, speedup=1.0, should_loop=False):
    """Publish sensor data to MQTT with appropriate timing."""
    if not sensor_data:
        print("No sensor data to publish.")
        return

    # First, we'll organize all the data points with their absolute timestamps
    all_data = []
    for sensor_name, data_points in sensor_data.items():
        for point in data_points:
            all_data.append({
                'sensor_name': sensor_name,
                'timestamp': point['timestamp'],
                'value': point['value'],
                'sensor_type': point['sensor_type']
            })

    # Sort all data points by timestamp
    all_data.sort(key=lambda x: x['timestamp'])

    while True:
        start_time = time.time()
        first_timestamp = all_data[0]['timestamp']

        for i, data_point in enumerate(all_data):
            # Calculate delay until this message should be sent
            if i > 0:
                time_diff = data_point['timestamp'] - all_data[i-1]['timestamp']
                # Convert to seconds if necessary and apply speedup
                if isinstance(time_diff, (int, float)):
                    delay = time_diff / speedup
                else:
                    # Assume timestamp is datetime
                    delay = time_diff.total_seconds() / speedup

                if delay > 0:
                    time.sleep(delay)

            # Publish the message
            sensor_type = data_point['sensor_type']
            topic = f"{TOPIC_PREFIXES[sensor_type]}/{data_point['sensor_name']}"
            message = str(data_point['value'])

            client.publish(topic, payload=message)
            print(f"Published to {topic}: {message} (timestamp: {data_point['timestamp']})")

        if not should_loop:
            break

        # If looping, wait until all messages have been sent before restarting
        elapsed = time.time() - start_time
        print(f"Completed one cycle in {elapsed:.2f} seconds. Restarting...")

def main():
    args = parse_args()

    # Verify the Excel file exists
    excel_path = os.path.abspath(args.excel_file)
    if not os.path.isfile(excel_path):
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)

    # Get available sheets/sensors
    sheet_names = get_excel_sheets(excel_path)

    # Either use command line args or prompt interactively
    if args.sensors or args.speedup != 1.0 or args.loop:
        selected_sensors = args.sensors.split(",") if args.sensors else sheet_names
        selected_sensors = [s for s in selected_sensors if s in sheet_names]
        speedup = args.speedup
        should_loop = args.loop
    else:
        selected_sensors = prompt_for_sensors(sheet_names)
        speedup = prompt_for_speedup()
        should_loop = prompt_for_loop()

    # Connect to MQTT broker
    client = connect_mqtt()

    try:
        # Read sensor data
        sensor_data = read_sensor_data(excel_path, selected_sensors)

        # Publish data
        publish_sensor_data(client, sensor_data, speedup, should_loop)

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        # Clean up MQTT connection
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
