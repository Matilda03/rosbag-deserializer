import csv
import ssl
import paho.mqtt.client as mqtt
import socket
import sys
import os
import argparse
import time

BROKER = "mqtt.dtlab.eaisi.tue.nl"
PORT = 8883
USERNAME = "matilda"  # Replace with actual username
PASSWORD = "cedalo1234"  # Replace with actual password
TLS_CA_CERTS = None  # Set to path of CA cert if needed, else None
TOPIC_PREFIX = "test/carTest/vehicle/status"

def transform_topic(original_topic):
    """
    Transforms the given MQTT topic by removing its leading path and appending a
    defined topic prefix. The resulting transformed topic will include only its
    suffix appended to the prefix.

    :param original_topic: Original MQTT topic as a string to be transformed.
    :return: A transformed topic string with the defined prefix followed by the
             suffix derived from the original topic.
    """
    # Remove leading slash and everything up to the last slash
    # Example: /sensing/gnss/ublox/fix_velocity -> fix_velocity
    topic_suffix = original_topic.strip().split("/")[-1]
    return f"{TOPIC_PREFIX}/{topic_suffix}"

def parse_args():
    """

    """
    parser = argparse.ArgumentParser(description="Publish messages from details.csv to MQTT.")
    parser.add_argument(
        "--topics",
        type=str,
        default="",
        help="Comma-separated list of topic suffixes to send (e.g., fix_velocity,fix_position). If omitted, all topics are sent."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Interval in seconds between sending messages (default: 0, i.e., as fast as possible)."
    )
    return parser.parse_args()

def get_available_topic_suffixes(csv_path):
    """
    Get available topic suffixes from a CSV file.

    This function processes a CSV file to extract the `topic`, `Topic`, `path`,
    or `Path` column contents, splits them to isolate the suffix (the last part
    after the last `/` in the value), and returns a sorted list of unique suffixes.

    :param csv_path: Path to the CSV file to process.
    :type csv_path: str
    :return: Sorted list of unique topic suffixes extracted from the CSV file.
    :rtype: list[str]
    """
    suffixes = set()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            original_topic = row.get("topic") or row.get("Topic") or row.get("path") or row.get("Path")
            if original_topic:
                suffix = original_topic.strip().split("/")[-1]
                suffixes.add(suffix)
    return sorted(suffixes)

def prompt_for_topics(suffixes):
    """
    Prompts the user to select topics from a list of suffixes, using their indices,
    and returns the selected topics as a set. If the input is invalid or empty,
    all topics will be selected by default.

    :param suffixes: A list of topic suffix options to choose from.
    :type suffixes: list[str]

    :return: A set of selected topic suffixes based on user input.
    :rtype: set[str]
    """
    print("Available topic suffixes:")
    for idx, suffix in enumerate(suffixes, 1):
        print(f"{idx}: {suffix}")
    print("Enter the numbers of the topics you want to send, separated by commas (e.g., 1,3,5), or press Enter to select all:")
    inp = input("> ").strip()
    if not inp:
        return set(suffixes)
    try:
        indices = [int(i) for i in inp.split(",") if i.strip()]
        selected = set(suffixes[i-1] for i in indices if 1 <= i <= len(suffixes))
        return selected
    except Exception:
        print("Invalid input, selecting all topics.")
        return set(suffixes)

def prompt_for_interval():
    """
    Prompts the user to input an interval in seconds for message timing and processes the input.

    The function allows the user to specify an interval in seconds between messages, defaulting
    to 0.0 (as fast as possible) if no input or invalid input is provided. Valid numeric input is
    returned, ensuring non-negative values are enforced.

    :raises ValueError: If invalid numeric input cannot be converted to a floating-point number.

    :return: The interval in seconds entered by the user, defaulting to 0.0 if no input
             or invalid input is provided. Non-negative float values are ensured.
    :rtype: float
    """
    print("Enter the interval in seconds between messages (e.g., 0.5), or press Enter for 0 (as fast as possible):")
    inp = input("> ").strip()
    if not inp:
        return 0.0
    try:
        val = float(inp)
        return max(0.0, val)
    except Exception:
        print("Invalid input, using 0.")
        return 0.0

def prompt_for_loop():
    """
    Prompts the user to decide on looping behavior for messages, including whether
    to loop and the number of times to loop.

    :return:
        Returns an integer specifying the number of loops (minimum 1), or None for
        infinite looping. Returns 1 if the user chooses not to loop.
    :rtype: int | None
    """
    print("Do you want to loop the messages? (y/n, default n):")
    inp = input("> ").strip().lower()
    if inp != "y":
        return 1  # No loop, just once
    print("Enter the number of times to loop (press Enter for infinite):")
    inp = input("> ").strip()
    if not inp:
        return None  # Infinite loop
    try:
        val = int(inp)
        return max(1, val)
    except Exception:
        print("Invalid input, looping infinitely.")
        return None

def main():
    """
    Main function responsible for handling the core logic of the program, including command-line argument
    parsing, interactive prompts, and MQTT client setup. The program processes a CSV file to publish
    messages to an MQTT broker based on specified topics and configured settings.

    :return: None
    """
    args = parse_args()
    csv_path = "details.csv"
    if not os.path.isfile(csv_path):
        print(f"ERROR: File '{csv_path}' not found in the current directory: {os.getcwd()}")
        sys.exit(1)

    # Interactive selection if no CLI args
    if not args.topics and args.interval == 0.0:
        suffixes = get_available_topic_suffixes(csv_path)
        selected_topics = prompt_for_topics(suffixes)
        interval = prompt_for_interval()
        loop_count = prompt_for_loop()
    else:
        selected_topics = set(t.strip() for t in args.topics.split(",") if t.strip()) if args.topics else None
        interval = args.interval
        loop_count = 1

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
    except Exception as e:
        print(f"ERROR: Could not connect to MQTT broker: {e}")
        sys.exit(1)

    def send_messages():
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                original_topic = row.get("topic") or row.get("Topic") or row.get("path") or row.get("Path")
                message = row.get("message") or row.get("Message") or row.get("data") or row.get("Data")
                if not original_topic or not message:
                    continue
                topic_suffix = original_topic.strip().split("/")[-1]
                if selected_topics and topic_suffix not in selected_topics:
                    continue
                new_topic = f"{TOPIC_PREFIX}/{topic_suffix}"
                client.publish(new_topic, payload=message)
                print(f"Published to {new_topic}: {message}")
                if interval > 0:
                    time.sleep(interval)

    try:
        if loop_count is None:
            print("Looping messages infinitely. Press Ctrl+C to stop.")
            while True:
                send_messages()
        else:
            for i in range(loop_count):
                print(f"Loop {i+1}/{loop_count}")
                send_messages()
    except KeyboardInterrupt:
        print("Interrupted by user.")

    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()