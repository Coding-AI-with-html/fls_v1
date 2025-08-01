import logging
from datetime import datetime
import os

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Extract message components
        timestamp = record.msg['Timestamp']
        num_tracks = record.msg['Tracks']
        operator_values = ', '.join(f"{float(x):.3f}" for x in record.msg['Operator_setpoints'])
        software_values = ', '.join(f"{float(x):.3f}" for x in record.msg['Processed_values'])
        quality = ', '.join(f"{float(x):.3f}" for x in record.msg['PV_quality'])
        image_id = record.msg['Image_name']
        view = record.msg['View_name']

        # Calculate required lengths dynamically
        timestamp_len = 20
        num_tracks_len = 5
        operator_values_len = max(50, len(operator_values))
        software_values_len = max(52, len(software_values))
        quality_len = max(52, len(quality))
        image_id_len = max(30, len(image_id))
        view_len = max(30, len(view))

        # Format the log entry with proper alignment
        log_entry = (
            f"{timestamp:<{timestamp_len}} "
            f"{num_tracks:<{num_tracks_len}} "
            f"{operator_values:<{operator_values_len}} "
            f"{software_values:<{software_values_len}} "
            f"{quality:<{quality_len}} "
            f"{image_id:<{image_id_len}} "
            f"{view:<{view_len}}\n"
        )
        return log_entry

# Function to write headers if not present
def write_headers_if_needed(log_file):
    if not os.path.isfile(log_file) or os.path.getsize(log_file) == 0:
        with open(log_file, 'w') as f:
            header = (
                f"{'Timestamp':<20} "
                f"{'Tracks':<10} "
                f"{'Operator_setpoints':<50} "
                f"{'Processed_values':<52} "
                f"{'PV_quality':<52} "
                f"{'Image_name':<30} "
                f"{'View_name':<30}\n"
            )
            f.write(header)
            # f.close()


def format_log_entry_numbers(entry: dict) -> dict:
    formatted_entry = entry.copy()
    keys_to_format = ['Operator_setpoints', 'Processed_values', 'PV_quality']
    for key in keys_to_format:
        if key in formatted_entry and isinstance(formatted_entry[key], list):
            formatted_entry[key] = [f"{val:.3f}" for val in formatted_entry[key]]
    return formatted_entry
