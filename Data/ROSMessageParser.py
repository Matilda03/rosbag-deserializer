import re

def read_message_details(file_path):
    """
    Reads the message details from a file and returns them as a dictionary.

    :param file_path: Path to the file containing message details.
    :return: Dictionary with message details.
    """
    message_details = {}

    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip():  # Ignore empty lines
                    key, value = line.split(':', 1)
                    message_details[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")

    return message_details



def parse_velocity_message(message):
    """
    Parses a velocity message in the format of geometry_msgs.msg.TwistWithCovarianceStamped
    and returns its linear_x, linear_y, and angular_z components.

    :param message: The velocity message string to parse.
    :return: A dictionary with parsed velocity components.
    """
    try:
        linear_x = float(re.search(r'linear=geometry_msgs\.msg\.Vector3\(x=([-\d\.e]+),', message).group(1))
        linear_y = float(re.search(r'linear=geometry_msgs\.msg\.Vector3\(x=[-\d\.e]+, y=([-\d\.e]+),', message).group(1))
        angular_z = float(re.search(r'angular=geometry_msgs\.msg\.Vector3\(x=[-\d\.e]+, y=[-\d\.e]+, z=([-\d\.e]+)\)', message).group(1))
        return {
            'linear_x': linear_x,
            'linear_y': linear_y,
            'angular_z': angular_z
        }
    except Exception as e:
        print(f"Error parsing velocity message: {e}")
        return None