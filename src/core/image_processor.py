import argparse
import asyncio
import glob
import os
from pathlib import Path
import shutil
import cv2
import numpy as np
from matplotlib import pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import configparser
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage
import threading
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from .custom_formatter import CustomFormatter,write_headers_if_needed, format_log_entry_numbers
from core.rename import get_unique_view_name
from .config import get_config_path
import time
import datetime 
import subprocess
from ctypes import Structure, c_char_p, c_int, c_ulong, c_char, c_uint16,  ARRAY, Array
from .text_logger import ErrorContext, FLS_ERR_NoErrorContext, FLS_ERR_NoUnprocessedImage, FLS_ERR_ImageProcessingFailed, get_logger




# Read configuration
config = configparser.ConfigParser()
config_path = get_config_path()
config.read(config_path)

# Set up logger
logger = logging.getLogger('customLogger')
logger.setLevel(logging.INFO)

loggerProgram = logging.getLogger("ImageProcessor")
#logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

# Global variables
#B


horizontal_lines = [0.2, 0.4, 0.6, 0.8, 1.0]  # Default values in normalized coordinates
horizontal_lines_colors = ['blue', 'blue', 'blue', 'blue', 'blue']  # Default colors
horizontal_lines_names = ['1', '2', '3', '4', '5']  # Default names
vertical_line_positions = []
software_values = []
#Hardcoded values 
resize_width = 1024
resize_height = 1024 
alert_messages = {
    'English': "Fire detected on the operator line.",
    'German': "Branddetektor auf dem Betreiber-Linie.",
    'Italian': "Detezione di fuoco sulla linea dell'operatore."
}
processing_done = False
latest_update = None
TRACKS_PER_VIEW_MAX = 8

max_views_supported = 4

approx_curve = None  # To store the green curved line
resized_cropped_contour_image = None  # Initialize it as None
image = None

MAX_PAST_TOLERANCE = 300      # 5 minutes
MAX_FUTURE_TOLERANCE = 120    # 2 minutes

def is_correct_time():
    current_time = datetime.datetime.now().time()
    return current_time.hour == 23 and current_time.minute == 57

def check_time_to_move_unprocessed_files(root_dir):
    
    if is_correct_time():
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        #folder_path = os.path.join(directory_from_fls, today)
        folder_path = os.path.join(root_dir, today)
        if not os.path.exists(folder_path):
            print("There is no folder created for today")
            os.makedirs(folder_path)

        # Move all .png files to the new folder
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith('.png'):
                    shutil.move(os.path.join(root, file), folder_path)

        print(f"Files moved to {folder_path}")
    else:
        loggerProgram.info("It's not the right time for moving unprocessed files")
        return

class PbBufInWic(Structure):
    _fields_ = [
        ("state1", c_uint16),       # max. 16 state bits set or throughput by master
        ("state2", c_uint16),       # max. 16 state bits set or throughput by master
        ("year", c_uint16),
        ("month", c_uint16),
        ("day", c_uint16),
        ("hours", c_uint16),
        ("minutes", c_uint16),
        ("seconds", c_uint16),
        ("interval1", c_uint16),
        ("interval2", c_uint16),
        ("interval3", c_uint16),
        ("interval4", c_uint16),
        ("value_13", c_uint16),
        ("value_14", c_uint16),
        ("value_15", c_uint16),
        ("value_16", c_uint16),     # used as watchdog value by the Profibus Master
        ("sp1", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("sp2", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("sp3", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("sp4", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
    ]

class PbBufOutWic(Structure):
    _pack_ = 2
    _fields_ = [
        ("state1", c_uint16),
        ("state2", c_uint16),
        ("year", c_uint16),
        ("month", c_uint16),
        ("day", c_uint16),
        ("hours", c_uint16),
        ("minutes", c_uint16),
        ("seconds", c_uint16),
        ("interval1", c_uint16),
        ("interval2", c_uint16),
        ("interval3", c_uint16),
        ("interval4", c_uint16),
        ("value_13", c_uint16),
        ("value_14", c_uint16),
        ("value_15", c_uint16),
        ("value_16", c_uint16),
        # Use ARRAY to create c_uint16 arrays
        ("pv1", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq1", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pv2", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq2", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pv3", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq3", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pv4", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq4", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
    ]

pb_buf_do_wic = PbBufInWic()
pb_buf_di_wic = PbBufOutWic()


# Function to update the state values
def update_state(data, state1, state2):
    data.state1 = state1
    data.state2 = state2

def update_only_state2(data, new_state2):
    # Pass the current value of state1 unchanged
    update_state(data, data.state1, new_state2)

def update_intervals_and_unvalues(data, interval1, interval2,interval3, interval4, unvalue1,  unvalue2,  unvalue3,  unvalue4):
    data.interval1 = interval1
    data.interval2 = interval2
    data.interval3 = interval3
    data.interval4 = interval4
    data.unused_value13  = unvalue1
    data.unused_value14  = unvalue2
    data.unused_value15  = unvalue3
    data.unused_value16  = unvalue4

# Function to update the timestamp
def update_timestamp(data, year, month, day, hours, minutes, seconds):
    data.year = year
    data.month = month
    data.day = day
    data.hours = hours
    data.minutes = minutes
    data.seconds = seconds

# Function to update process values and setpoints
def update_process_values(pb_buf_di_wic, software_values, piece_qualities, view_idx):
    """Update process values (pv1-pv4) and quality values (pvq1-pvq4) based on view index.
    Unused views are not overwritten and retain their previous values."""

    # Define maximum size for each array
    max_size = TRACKS_PER_VIEW_MAX 

    def fill_with_zeros(length):
        """Return a list of zeros with the specified length."""
        return [0] * length

    def fill_and_pad(values, length, multiply_software=False):
        """Ensure the array has exactly length elements, padding with zeros if necessary.
        Multiply software values by 10000 if required."""
        if multiply_software:
            values = [round(value * 10000) if value is not None else 0 for value in values]
        return values + [0] * (length - len(values))

    # Fill the current view's software values and piece qualities
    software_values_filled = fill_and_pad(software_values, max_size, multiply_software=True)
    piece_qualities_filled = fill_and_pad(piece_qualities, max_size)

    # Convert lists to ctypes arrays
    software_values_array = ARRAY(c_uint16, max_size)(*software_values_filled)
    piece_qualities_array = ARRAY(c_uint16, max_size)(*piece_qualities_filled)

    # Update the correct view's arrays
    if view_idx == 0:
        pb_buf_di_wic.pv1 = software_values_array
        pb_buf_di_wic.pvq1 = piece_qualities_array
    elif view_idx == 1:
        pb_buf_di_wic.pv2 = software_values_array
        pb_buf_di_wic.pvq2 = piece_qualities_array
    elif view_idx == 2:
        pb_buf_di_wic.pv3 = software_values_array
        pb_buf_di_wic.pvq3 = piece_qualities_array
    elif view_idx == 3:
        pb_buf_di_wic.pv4 = software_values_array
        pb_buf_di_wic.pvq4 = piece_qualities_array




def numpy_array_to_floats(array):
    return [float(x) if x is not None else 0.0 for x in array]

def process_latest_image(image_directory):
    """Process the latest image without looping."""
    latest_image = get_latest_image(image_directory)
    if latest_image:
        print(f"Processing latest image: {latest_image}")
        process_image_with_multiple_sub_images(latest_image)
    else:
        print("No unprocessed image to process.")


def check_and_update_interval(interval1, detection_interval, config):
    """
    Checks if interval1 matches the configured detection_interval.
    If interval1 does not match, update the config file with the new interval.

    Args:
        interval1 (int): The first interval received from the operator.
        detection_interval (int): The detection interval from the config.
        config (configparser.ConfigParser): The config object to modify if the interval doesn't match.

    Returns:
        int: The possibly updated interval1.
    """
    if interval1 != detection_interval:
        # Update config with the new detection_interval from Operator
        config.set("Settings", "detection_interval", str(interval1))
        #log_message("Changed detection interval")
        # Write the updated config back to the file
        with open('fls.cfg', 'w') as configfile:
            config.write(configfile)

        print(f"Config file updated. New detection_interval: {interval1}")

        return interval1  # Return the interval

    return detection_interval  # Return the original config interval if it matches
# Adjusted section of send_and_receive_data function
def update_pb_in_struct(image_context):
    """
    Transfers data from image_context.data_read to pb_buf_do_wic and prints the updated values.

    Args:
        image_context: An object containing data_read with fields to update pb_buf_do_wic.
    """
    try:
        # Assign scalar fields
        update_state(pb_buf_do_wic, image_context.data_read.state1, image_context.data_read.state2)
        update_timestamp(
            pb_buf_do_wic,
            image_context.data_read.year,
            image_context.data_read.month,
            image_context.data_read.day,
            image_context.data_read.hours,
            image_context.data_read.minutes,
            image_context.data_read.seconds,
        )
        update_intervals_and_unvalues(
            pb_buf_do_wic,
            image_context.data_read.interval1,
            image_context.data_read.interval2,
            image_context.data_read.interval3,
            image_context.data_read.interval4,
            image_context.data_read.value_13,
            image_context.data_read.value_14,
            image_context.data_read.value_15,
            image_context.data_read.value_16,
        )

        # Assign array fields
        pb_buf_do_wic.sp1[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp1)
        pb_buf_do_wic.sp2[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp2)
        pb_buf_do_wic.sp3[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp3)
        pb_buf_do_wic.sp4[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp4)

        # Log updated values
       

    except AttributeError as e:
        print(f"Error: Missing attribute in image_context.data_read: {e}")
        loggerProgram.error(f"Error: Missing attribute in image_context.data_read: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        loggerProgram.error(f"An unexpected error occurred: {e}")


def update_pb_do_struct(image_context):
    """
    Transfers data from image_context.data_read to pb_buf_do_wic and prints the updated values.

    Args:
        image_context: An object containing data_read with fields to update pb_buf_do_wic.
    """

    try:
        # Assign scalar fields
        update_state(pb_buf_di_wic, image_context.data_read.state1, image_context.data_read.state2)
        update_timestamp(
            pb_buf_di_wic,
            image_context.data_read.year,
            image_context.data_read.month,
            image_context.data_read.day,
            image_context.data_read.hours,
            image_context.data_read.minutes,
            image_context.data_read.seconds,
        )
        update_intervals_and_unvalues(
            pb_buf_di_wic,
            image_context.data_read.interval1,
            image_context.data_read.interval2,
            image_context.data_read.interval3,
            image_context.data_read.interval4,
            image_context.data_read.value_13,
            image_context.data_read.value_14,
            image_context.data_read.value_15,
            image_context.data_read.value_16,
        )

        # Assign array fields
        pb_buf_di_wic.pv1[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_write.pv1)
        pb_buf_di_wic.pv2[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_write.pv2)
        pb_buf_di_wic.pv3[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_write.pv3)
        pb_buf_di_wic.pv4[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_write.pv4)

        # Log updated values
       

    except AttributeError as e:
        print(f"Error: Missing attribute in image_context.write: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def update_pb_in_setpoints(image_context):

    
    """
    Transfers data from image_context.data_read to pb_buf_do_wic and prints the updated values.

    Args:
        image_context: An object containing data_read with fields to update pb_buf_do_wic.
    """
    try:
        # Assign array fields
        pb_buf_do_wic.sp1[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp1)
        pb_buf_do_wic.sp2[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp2)
        pb_buf_do_wic.sp3[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp3)
        pb_buf_do_wic.sp4[:] = (c_uint16 * TRACKS_PER_VIEW_MAX)(*image_context.data_read.sp4)

        # Log updated values
       

    except AttributeError as e:
        print(f"Error: Missing attribute in image_context.data_read: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def print_struct_PB(struct_instance):
    for field_name, field_type in struct_instance._fields_:
        value = getattr(struct_instance, field_name)
        # Check if the field type is an array
        if issubclass(field_type, Array):
            print(f"{field_name}:")
            for i, elem in enumerate(value):
                print(f"  [{i}]: {elem}")
        else:
            print(f"{field_name}: {value}")


# Function to calculate sharpness using the Laplacian variance
def calculate_sharpness(image):
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    variance = laplacian.var()
    return variance


# Function to calculate noise level using standard deviation
def calculate_noise(image):
    return np.std(image)


# Function to calculate brightness and contrast
def calculate_brightness_contrast(image):
    brightness = np.mean(image)
    contrast = image.std()
    return brightness, contrast


# Normalize a value to a range [0, 1]
def normalize(value, min_value, max_value):
    return (value - min_value) / (max_value - min_value)

def calculate_general_quality(sharpness, noise, brightness, contrast):
    # Define ideal ranges for each metric
    sharpness_min, sharpness_max = 0, 200  # Laplacian variance range
    noise_min, noise_max = 0, 100  # Standard deviation range
    brightness_min, brightness_max = 50, 200  # Desired brightness range
    contrast_min, contrast_max = 10, 100  # Desired contrast range

    # Normalize metrics
    sharpness_score = normalize(sharpness, sharpness_min, sharpness_max)
    noise_score = 1 - normalize(noise, noise_min, noise_max)  # Lower noise is better
    brightness_score = 1 - abs(normalize(brightness, brightness_min,
                                         brightness_max) - 0.5) * 2  # Ideal brightness is in the middle of the range
    contrast_score = normalize(contrast, contrast_min, contrast_max)

    # Combine the normalized scores into a single quality score
    overall_score = (sharpness_score * 0.4) + (noise_score * 0.2) + (brightness_score * 0.2) + (contrast_score * 0.2)

    return overall_score

def create_log_file(data, base_directory):
    today =datetime.datetime.now().strftime('%Y-%m-%d')
    #folder_path = os.path.join(base_directory, today)
    #if not os.path.exists(folder_path):
    #    os.makedirs(folder_path)

    log_file = os.path.join(base_directory, f'logfile_{today}.log')
    write_headers_if_needed(log_file)
    logger = logging.getLogger('customLogger')
    logger.handlers.clear()  # Remove all existing handlers
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    formatter = CustomFormatter()
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info(data)


def create_log_same_folder(data, base_directory):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(base_directory, f'logfile_{today}.log')
    write_headers_if_needed(log_file)
    
    logger = logging.getLogger('customLogger')
    logger.handlers.clear()
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    formatter = CustomFormatter()
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info(data)
def failed_processing_result(image_context):
    now = datetime.datetime.now()

    if not image_context or not image_context.data_read:
        loggerProgram.warning("Image context is empty or None.")
        return False, None

    # Fill timestamp fields
    
    pb_buf_di_wic.state1 = 1
    pb_buf_di_wic.state2 = 0
    pb_buf_di_wic.year = now.year
    pb_buf_di_wic.month = now.month
    pb_buf_di_wic.day = now.day
    pb_buf_di_wic.hours = now.hour
    pb_buf_di_wic.minutes = now.minute
    pb_buf_di_wic.seconds = now.second


    update_intervals_and_unvalues(
            pb_buf_di_wic,
            image_context.data_read.interval1,
            image_context.data_read.interval2,
            image_context.data_read.interval3,
            image_context.data_read.interval4,
            image_context.data_read.value_13,
            image_context.data_read.value_14,
            image_context.data_read.value_15,
            image_context.data_read.value_16,
        )

    for i in range(TRACKS_PER_VIEW_MAX):
        pb_buf_di_wic.pv1[i] = 0
        pb_buf_di_wic.pvq1[i] = 0
        pb_buf_di_wic.pv2[i] = 0
        pb_buf_di_wic.pvq2[i] = 0
        pb_buf_di_wic.pv3[i] = 0
        pb_buf_di_wic.pvq3[i] = 0
        pb_buf_di_wic.pv4[i] = 0
        pb_buf_di_wic.pvq4[i] = 0

    return False, pb_buf_di_wic

def put_proccesed_image_into_sub_today_folder(image_path, base_dir):
    try:
        shutil.move(image_path, base_dir)
    except Exception as e:
        print(f"Could not move image '{image_path}' to '{base_dir}': {e}")
        loggerProgram.warning("Could not move image")

def create_folder_for_today(plot, filename, base_dir):
    # Get the current date and format it as 'DD-MM'
    #today = datetime.datetime.now().strftime('%Y-%m-%d')

    # Create the full path for the folder to be created
    #folder_path = os.path.join(base_dir, today)

    # Check if the folder already exists
    #if not os.path.exists(folder_path):
    #    os.makedirs(folder_path)

    plot_path = os.path.join(base_dir, f"{filename}")
    plot.savefig(plot_path)


def scale_setpoints(setpoints):
    """Scale the setpoints by dividing each value by 10,000."""
    return [value / 10000 for value in setpoints]

# Function to convert integer to floating point
def int_to_float(value: int) -> float:
    return float(value)

def get_bit(value, n):
    return ((value >> n & 1) != 0)

def set_bit(value, n):
    return value | (1 << n)

def clear_bit(value, n):
    return value & ~(1 << n)


#print(f"Active threads: {[t.name for t in threading.enumerate()]}")
# Function to detect fire regions
def detect_fire_regions(image):
    # Make a copy of the input image
    img_copy = image.copy()

    # Convert the image to HSV color space
    hsv = cv2.cvtColor(img_copy, cv2.COLOR_BGR2HSV)

    # Define the threshold for bright regions (typical for fire)
    lower_bright = np.array([0, 20, 225])
    upper_bright = np.array([35, 255, 255])

    # Threshold the HSV image to get only bright regions
    mask = cv2.inRange(hsv, lower_bright, upper_bright)

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area to remove small regions and noise
    min_contour_area = 100  # Adjust this threshold based on image size and requirements
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

    return filtered_contours


def calculate_laplacian_variance(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var


def process_image_with_multiple_sub_images(image_context, image_path, result_dir, create_log='Yes', manually='No'):
    global resized_cropped_contour_image, vertical_line_positions, approx_curve, output_image, software_values, file_name


    if not image_context or not image_context.data_read:
        loggerProgram.warning("Image context is empty or None.")
        return False, None
    
    try:
        loggerProgram.info("Starting image processing")
        now = datetime.datetime.now()

        try:
            asyncio.run(check_timestamp_async(os.path.basename(image_path)))
        except RuntimeError:
        # Handle case where there's already an event loop running (e.g., in GUI apps)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(check_timestamp_async(os.path.basename(image_path)))
            else:
                loop.run_until_complete(check_timestamp_async(os.path.basename(image_path)))
        
        # Update the timestamp in the structure
        pb_buf_di_wic.year = now.year
        pb_buf_di_wic.month = now.month
        pb_buf_di_wic.day = now.day
        pb_buf_di_wic.hours = now.hour
        pb_buf_di_wic.minutes = now.minute
        pb_buf_di_wic.seconds = now.second

        # Extract values from the structure
        

        file_name = os.path.basename(image_path)
        file_name_no_ext, file_ext = os.path.splitext(file_name)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_image = None

        image = cv2.imread(image_path)
        if image is None:
            #log_message(f"Error loading image {file_name}", "ERROR")
            print(f"Error loading image {file_name}")
            update_state(pb_buf_di_wic, 1, pb_buf_di_wic.state2)
            return

        # Read the rectangles' coordinates from the config file
        config.read('fls.cfg')
        # Check if there is declared views in config file, and if there is not, then make one whole as default
        if 'Selected_Views' not in config or not config.options('Selected_Views'):
            if 'Selected_Views' not in config:
                config.add_section('Selected_Views')

            # Set the full image as the default view
            full_image_view = [0, 0, image.shape[1], image.shape[0]]  # Full image
            config.set('Selected_Views', 'View_1', str(full_image_view))

            # Write this default view back to the config file
            with open('fls.cfg', 'w') as configfile:
                config.write(configfile)
        rectangles = config.items('Selected_Views')
        rectangles = [(int(coords.split(',')[0][1:]), int(coords.split(',')[1]), int(coords.split(',')[2]), int(coords.split(',')[3][:-1])) for key, coords in rectangles]

        number_of_tracks = config.getint('Settings', 'number_of_tracks')

        

        max_variance = 100.0
        processed_views = 0
        view_bitmask = 0
        # List to store the qualities for each view
        all_views_piece_qualities = []
        all_software_values = []  # New list to store software values for all views
        sp_values = [pb_buf_do_wic.sp1, pb_buf_do_wic.sp2, pb_buf_do_wic.sp3,
                    pb_buf_do_wic.sp4]  # Setpoint arrays sp1, sp2, sp3, sp4
        #print("Setpointss in function")
        #print(sp_values)
        for idx, (x1, y1, x2, y2) in enumerate(rectangles):
            # Crop the rectangle from the image
            cropped_image = image[y1:y2, x1:x2]
            resized_cropped_image = cv2.resize(cropped_image, (resize_width, resize_height))

            current_sp_values = [value / 10000 for value in sp_values[idx % len(sp_values)]]

            # Commas Thing- adjustment based on the number of tracks selected

            current_sp_values = current_sp_values[:number_of_tracks]
            #if len(current_sp_values) > number_of_tracks:
            #    current_sp_values = current_sp_values[:number_of_tracks] + [','] * (len(current_sp_values) - number_of_tracks)
            #else:
            #    current_sp_values += [','] * (number_of_tracks - len(current_sp_values))

            piece_width = resize_width // number_of_tracks
            pieces = [resized_cropped_image[:, i * piece_width:(i + 1) * piece_width] for i in range(number_of_tracks)]

            # Array to hold the quality of each piece for this view
            piece_qualities = []
            # Array to hold quality for each piece for logfile
            piece_qualities_base = []

            fig, axes = plt.subplots(1, number_of_tracks, figsize=(20, 4))
            highest_points_all_pieces = []
            view_is_used = False

            for i, ax in enumerate(axes):
                piece = pieces[i]
                sharpness = calculate_sharpness(piece)
                noise = calculate_noise(piece)
                brightness, contrast = calculate_brightness_contrast(piece)
                contours = detect_fire_regions(piece)

                # Calculate quality for each piece and append it to piece_qualities

                #laplacian_variance = calculate_laplacian_variance(piece)
                quality_score = calculate_general_quality(sharpness, noise, brightness, contrast)
                #print("laplacian: ", laplacian_variance)
                piece_quality = round(min(quality_score, 1.0), 2)# Quality for this piece
                #print("Quality of piece Sharpens blur: ", sharpness_blur)

                piece_qualities_base.append(piece_quality)
                rounded_quality_piece = round(piece_quality * 10000)
                piece_qualities.append(rounded_quality_piece)  # Store each piece quality

                if contours:
                    longest_contour = max(contours, key=lambda cnt: cv2.arcLength(cnt, True))
                    lowest_points = [point for point in longest_contour if point[0][1] > piece.shape[0] * 0.61]
                    view_is_used = True
                    if lowest_points:
                        lowest_point = max(lowest_points, key=lambda point: point[0][1])
                        lowest_y = lowest_point[0][1]
                        cv2.line(piece, (0, lowest_y), (piece.shape[1] - 1, lowest_y), (0, 255, 0), 4)
                        normalized_y_coord = lowest_y / piece.shape[0]
                        highest_points_all_pieces.append((i * piece_width, lowest_y))
                    else:
                        highest_points_all_pieces.append((i * piece_width, None))
                else:
                    highest_points_all_pieces.append((i * piece_width, None))

            if view_is_used:
                # Set the bit for this view in the bitmask if it's used
                view_bitmask = set_bit(view_bitmask, idx)
                processed_views += 1

            all_views_piece_qualities.append(piece_qualities)
            software_values = []
            for point in highest_points_all_pieces:
                if point[1] is not None:
                    normalized_y_coord = point[1] / resized_cropped_image.shape[0]
                    round_num = round(normalized_y_coord, 2)
                    software_values.append(round_num)
                else:
                    software_values.append(None)
            # Append the software values of this view to the list of all software values
            all_software_values.append(software_values)
            logfile_software_values = numpy_array_to_floats(software_values)
    
            piece_qualities_base = numpy_array_to_floats(piece_qualities_base)
            view = f"{file_name_no_ext}_#{idx + 1}{file_ext}" if len(rectangles) > 1 else f"{file_name_no_ext}_#{idx + 1}{file_ext}"
            if manually == "Yes":
                unique_view_name = get_unique_view_name(view, result_dir)
                view = unique_view_name

            data = {
                "Timestamp": timestamp,
                'Tracks': number_of_tracks,
                "Operator_setpoints": current_sp_values,
                "Processed_values": logfile_software_values, 
                "PV_quality": piece_qualities_base,  # Include the array of piece qualities for this view
                "Image_name": file_name,
                "View_name": view
            }
            final_data = format_log_entry_numbers(data)
            #create_log_file(data, result_dir)

            if create_log == 'Yes':
               create_log_file(final_data, result_dir)
            else:
                create_log_same_folder(final_data, result_dir)
            #print(f"Data to be logged for view {idx + 1}: {data}")
            # After processing all views, convert np.float64 to float

            #software_values = [round(value * 10000) if value is not None else None for value in software_values]
            unvalues = [0, 0, 0, 0]  # Initially, assume all views are unused (set to 1)

            # Set the first `processed_views` unvalues to 0, meaning those were processed
            for i in range(processed_views):
                unvalues[i] = 1  # Mark successfully processed views as used (set to 0)

            # Assign the calculated unvalues
            unvalue1, unvalue2, unvalue3, unvalue4 = unvalues

            #print("All Sofware_val:", all_software_values)
            update_process_values(pb_buf_di_wic, software_values, piece_qualities, idx)
            update_only_state2(pb_buf_di_wic, view_bitmask)
            update_intervals_and_unvalues(pb_buf_di_wic, pb_buf_do_wic.interval1, pb_buf_do_wic.interval2, pb_buf_do_wic.interval3,pb_buf_do_wic.interval4, unvalue1, unvalue2, unvalue3, unvalue4)
            #print_struct_PB(pb_buf_di_wic)

            #print("pb_buf_do_wic.pvq4:", pb_buf_do_wic.pv4)
            #sort_data_by_view(idx, pb_buf_do_wic)
            #log_message("Image was proccesed", "DEBUG")

            resized_cropped_contour_image = resized_cropped_image.copy()

            if number_of_tracks > 1:
                num_lines = number_of_tracks - 1
            else:
                num_lines = number_of_tracks

            vertical_line_positions = [int(i * (resized_cropped_image.shape[1] / (num_lines + 1))) for i in
                                    range(1, num_lines + 1)]
            
            try:
                save_view_as_image(resized_cropped_image, vertical_line_positions, view, sp_values[idx % len(sp_values)], number_of_tracks, result_dir)
            except Exception as e:
                print(f"Error during saving plot: {e}")
            # update_plot()
        return True, pb_buf_di_wic
    except Exception as e:
        print(f"Error during processing: {e}")
        return False, None  # Return failure and None in case of error

    
def reprocess_after_manually_pv_injection(sim_cntx_read, sim_cntx_write,picked_image_path, result_dir, create_log='Yes', manually='Yes'):

    print("SPP:", sim_cntx_read.sp1)

    
    try:
        loggerProgram.info("Starting image re-processing")
        
        now = datetime.datetime.now()

        try:
            asyncio.run(check_timestamp_async(os.path.basename(picked_image_path)))
        except RuntimeError:
        # Handle case where there's already an event loop running (e.g., in GUI apps)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(check_timestamp_async(os.path.basename(picked_image_path)))
            else:
                loop.run_until_complete(check_timestamp_async(os.path.basename(picked_image_path)))
        
        # Update the timestamp in the structure
        pb_buf_di_wic.year = now.year
        pb_buf_di_wic.month = now.month
        pb_buf_di_wic.day = now.day
        pb_buf_di_wic.hours = now.hour
        pb_buf_di_wic.minutes = now.minute
        pb_buf_di_wic.seconds = now.second

        # Extract values from the structure

        try:
            asyncio.run(check_struct_time_async(pb_buf_di_wic))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(check_struct_time_async(pb_buf_di_wic))
            else:
                loop.run_until_complete(check_struct_time_async(pb_buf_di_wic))
        

        file_name = os.path.basename(picked_image_path)
        file_name_no_ext, file_ext = os.path.splitext(file_name)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_image = None

        image = cv2.imread(picked_image_path)
        if image is None:
            #log_message(f"Error loading image {file_name}", "ERROR")
            print(f"Error loading image {file_name}")
            update_state(pb_buf_di_wic, 1, pb_buf_di_wic.state2)
            return

        # Read the rectangles' coordinates from the config file
        config.read('fls.cfg')
        # Check if there is declared views in config file, and if there is not, then make one whole as default
        if 'Selected_Views' not in config or not config.options('Selected_Views'):
            if 'Selected_Views' not in config:
                config.add_section('Selected_Views')

            # Set the full image as the default view
            full_image_view = [0, 0, image.shape[1], image.shape[0]]  # Full image
            config.set('Selected_Views', 'View_1', str(full_image_view))

            # Write this default view back to the config file
            with open('fls.cfg', 'w') as configfile:
                config.write(configfile)
        rectangles = config.items('Selected_Views')
        rectangles = [(int(coords.split(',')[0][1:]), int(coords.split(',')[1]), int(coords.split(',')[2]), int(coords.split(',')[3][:-1])) for key, coords in rectangles]

        number_of_tracks = config.getint('Settings', 'number_of_tracks')

        

        max_variance = 100.0
        processed_views = 0
        view_bitmask = 0
        # List to store the qualities for each view
        all_views_piece_qualities = []
        all_software_values = []  # New list to store software values for all views

        sp_values = [sim_cntx_read.sp1, sim_cntx_read.sp2, sim_cntx_read.sp3,
                    sim_cntx_read.sp4]  # Setpoint arrays sp1, sp2, sp3, sp4
    
        #print("Setpointss in function")
        #print(sp_values)
        for idx, (x1, y1, x2, y2) in enumerate(rectangles):
            # Crop the rectangle from the image
            cropped_image = image[y1:y2, x1:x2]
            resized_cropped_image = cv2.resize(cropped_image, (resize_width, resize_height))

            current_sp_values = [value / 10000 for value in sp_values[idx % len(sp_values)]]

            # Commas Thing- adjustment based on the number of tracks selected

            current_sp_values = current_sp_values[:number_of_tracks]
            #if len(current_sp_values) > number_of_tracks:
            #    current_sp_values = current_sp_values[:number_of_tracks] + [','] * (len(current_sp_values) - number_of_tracks)
            #else:
            #    current_sp_values += [','] * (number_of_tracks - len(current_sp_values))

            piece_width = resize_width // number_of_tracks
            pieces = [resized_cropped_image[:, i * piece_width:(i + 1) * piece_width] for i in range(number_of_tracks)]

            # Array to hold the quality of each piece for this view
            piece_qualities = []
            # Array to hold quality for each piece for logfile
            piece_qualities_base = []

            fig, axes = plt.subplots(1, number_of_tracks, figsize=(20, 4))
            highest_points_all_pieces = []
            view_is_used = False

            for i, ax in enumerate(axes):
                piece = pieces[i]
                sharpness = calculate_sharpness(piece)
                noise = calculate_noise(piece)
                brightness, contrast = calculate_brightness_contrast(piece)
                contours = detect_fire_regions(piece)

                # Calculate quality for each piece and append it to piece_qualities

                #laplacian_variance = calculate_laplacian_variance(piece)
                quality_score = calculate_general_quality(sharpness, noise, brightness, contrast)
                #print("laplacian: ", laplacian_variance)
                piece_quality = round(min(quality_score, 1.0), 2)# Quality for this piece
                #print("Quality of piece Sharpens blur: ", sharpness_blur)

                piece_qualities_base.append(piece_quality)
                rounded_quality_piece = round(piece_quality * 10000)
                piece_qualities.append(rounded_quality_piece)  # Store each piece quality

                pv_values = [sim_cntx_write.pv1, sim_cntx_write.pv2, sim_cntx_write.pv3, sim_cntx_write.pv4]


                if idx < len(pv_values):
                    software_values = list(pv_values[idx])
                else:
                    print(f"[WARNING] View index {idx} exceeds available PV arrays. Using zeros.")
                    software_values = [0] * 8
                
                
                # Append the software values of this view to the list of all software values

                current_pv_values = [value / 10000 for value in pv_values[idx % len(pv_values)]]
                current_pv_values = current_pv_values[:number_of_tracks]

                if i < len(current_pv_values):
                    pv_value = current_pv_values[i]
                    if 0.0 <= pv_value <= 1.0:  # Ensure it's normalized
                        pv_y = int(pv_value * piece.shape[0])
                        cv2.line(piece, (0, pv_y), (piece.shape[1] - 1, pv_y), (0, 255, 0), 4)
                        view_is_used = True
                        highest_points_all_pieces.append((i * piece_width, pv_y))
                    else:
                        highest_points_all_pieces.append((i * piece_width, None))
                else:
                    highest_points_all_pieces.append((i * piece_width, None))

            if view_is_used:
                # Set the bit for this view in the bitmask if it's used
                view_bitmask = set_bit(view_bitmask, idx)
                processed_views += 1

            all_views_piece_qualities.append(piece_qualities)

            all_software_values.append(software_values)
            logfile_software_values = numpy_array_to_floats(current_pv_values)
            piece_qualities_base = numpy_array_to_floats(piece_qualities_base)
            view = f"{file_name_no_ext}_#{idx + 1}{file_ext}" if len(rectangles) > 1 else f"{file_name_no_ext}_#{idx + 1}{file_ext}"
            if manually == "Yes":
                unique_view_name = get_unique_view_name(view, result_dir)
                view = unique_view_name

            data = {
                "Timestamp": timestamp,
                'Tracks': number_of_tracks,
                "Operator_setpoints": current_sp_values,
                "Processed_values": logfile_software_values, 
                "PV_quality": piece_qualities_base,  # Include the array of piece qualities for this view
                "Image_name": file_name,
                "View_name": view
            }
            final_data = format_log_entry_numbers(data)
            #create_log_file(data, result_dir)

            if create_log == 'Yes':
               create_log_same_folder(final_data, result_dir)
            else:
                create_log_same_folder(final_data, result_dir)
            #print(f"Data to be logged for view {idx + 1}: {data}")
            # After processing all views, convert np.float64 to float

            #software_values = [round(value * 10000) if value is not None else None for value in software_values]
            unvalues = [0, 0, 0, 0]  # Initially, assume all views are unused (set to 1)

            # Set the first `processed_views` unvalues to 0, meaning those were processed
            for i in range(processed_views):
                unvalues[i] = 1  # Mark successfully processed views as used (set to 0)

            # Assign the calculated unvalues
            unvalue1, unvalue2, unvalue3, unvalue4 = unvalues

            #print("All Sofware_val:", all_software_values)
            update_process_values(pb_buf_di_wic, software_values, piece_qualities, idx)
            update_only_state2(pb_buf_di_wic, view_bitmask)
            update_intervals_and_unvalues(pb_buf_di_wic, pb_buf_do_wic.interval1, pb_buf_do_wic.interval2, pb_buf_do_wic.interval3,pb_buf_do_wic.interval4, unvalue1, unvalue2, unvalue3, unvalue4)
            #print_struct_PB(pb_buf_di_wic)

            #print("pb_buf_do_wic.pvq4:", pb_buf_do_wic.pv4)
            #sort_data_by_view(idx, pb_buf_do_wic)
            #log_message("Image was proccesed", "DEBUG")

            resized_cropped_contour_image = resized_cropped_image.copy()

            if number_of_tracks > 1:
                num_lines = number_of_tracks - 1
            else:
                num_lines = number_of_tracks

            vertical_line_positions = [int(i * (resized_cropped_image.shape[1] / (num_lines + 1))) for i in
                                    range(1, num_lines + 1)]
            
            try:
                save_view_as_image(resized_cropped_image, vertical_line_positions, view, sp_values[idx % len(sp_values)], number_of_tracks, result_dir)
            except Exception as e:
                print(f"Error during saving plot: {e}")
            # update_plot()
        return True, pb_buf_di_wic
    except Exception as e:
        print(f"Error during processing: {e}")
        return False, None  # Return failure and None in case of error



def parse_filename_to_datetime(filename: str) -> datetime.datetime | None:
    try:
        base = os.path.basename(filename)
        name, _ = os.path.splitext(base)
        return datetime.datetime.strptime(name, "%Y-%m-%d_%H-%M-%S")
    except Exception as e:
        logging.warning(f"Failed to parse timestamp from filename '{filename}': {e}")
        return None

async def check_timestamp_async(filename: str):
    timestamp = parse_filename_to_datetime(filename)
    if not timestamp:
        return

    now = datetime.datetime.now()
    delta = (timestamp - now).total_seconds()

    if delta < -MAX_PAST_TOLERANCE:
        loggerProgram.warning(f"File '{filename}' timestamp is too far in the past ({-delta:.1f} seconds).")
    #elif delta > MAX_FUTURE_TOLERANCE:
      #  logging.warning(f"File '{filename}' timestamp is too far in the future ({delta:.1f} seconds).")
    else:
        loggerProgram.info("OBS capture is in sync")



async def check_struct_time_async(pb_buf):
    try:
        # Create datetime from struct fields
        struct_time = datetime.datetime(
            pb_buf.year,
            pb_buf.month,
            pb_buf.day,
            pb_buf.hours,
            pb_buf.minutes,
            pb_buf.seconds
        )

        now = datetime.datetime.now()
        delta = (struct_time - now).total_seconds()

        if delta < -MAX_PAST_TOLERANCE:
            logging.warning(f"Struct timestamp is too far in the past ({-delta:.1f} seconds).")
        elif delta > MAX_FUTURE_TOLERANCE:
            logging.warning(f"Struct timestamp is too far in the future ({delta:.1f} seconds).")
        else:
            loggerProgram.info("Profibus client is in sync with profibus server")
    except Exception as e:
        loggerProgram.error(f"Error checking timestamp: {e}")


def get_latest_image(directory):
    all_png_files = glob.glob(os.path.join(directory, '*.png'))

    if not all_png_files:
        loggerProgram.warning(f"No .png files found in directory: {directory}")
        print(f"No .png files found in directory: {directory}")
        return None

    # Filter out any images that have already been processed
    unprocessed_files = [img for img in all_png_files if '_#' not in os.path.basename(img)]

    if not unprocessed_files:
        loggerProgram.warning(f"No unprocessed .png files found in {directory}")
        return None

    # Return the latest unprocessed image based on modification/creation time
    latest_unprocessed_image = max(unprocessed_files, key=os.path.getctime)
    return latest_unprocessed_image



def print_image_context(image_context):
    """
    Prints the contents of the image_context in a readable format.

    :param image_context: An instance of ImageContext containing intervals and setpoints data.
    """

    loggerProgram.debug(" Starting debugging Image Context")

    if not image_context or not image_context.data_read:
        loggerProgram.debug("Image context is empty or None.")
        return

    # Access data_read which contains intervals and setpoints
    data_read = image_context.data_read

    # Print intervals (assuming they are in data_read as a dictionary)
    loggerProgram.debug("\nIntervals:")
    try:
        # Access intervals from data_read
        intervals = data_read.get("intervals", {})
        if intervals:
            for key, value in intervals.items():
                print(f"{key}: {value}")
        else:
            loggerProgram.debug("No intervals data found in data_read.")
    except AttributeError:
        loggerProgram.debug("No intervals data in image_context.")

    # Print setpoints
    loggerProgram.debug("\nSetpoints:")
    try:
        # Access setpoints from data_read
        setpoints = data_read.get("setpoints", {})
        if setpoints:
            for sp_key, sp_values in setpoints.items():
                loggerProgram.debug(f"{sp_key}: {sp_values}")
        else:
            loggerProgram.debug("No setpoints data found in data_read.")
    except AttributeError:
        loggerProgram.debug("No setpoints data in image_context.")

def getResult(image_context, images_directory):
    ErrorLogger = get_logger("Image Processor")
    error_context = ErrorContext(logger=ErrorLogger)

    if not image_context or not image_context.data_read:
        logger.error("There is no processed image to take context")
        return None

    latest_image = get_latest_image(images_directory)
    update_pb_in_struct(image_context)

    if latest_image:
        ErrorLogger.info(f"Processing latest image: {latest_image}")
        try:
            success, result = process_image_with_multiple_sub_images(image_context, latest_image, images_directory)

            ErrorLogger.info(f"Processed image: {latest_image}")
            ErrorLogger.info(f"Success: {success}")
            ErrorLogger.info(f"Result: {result}")
            ErrorLogger.info(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            try:
                with open(config_path, 'r') as f:
                    config.read_file(f)

                root_result_path = get_cleaned_path("Settings", "root_archive")
            except e:
                print("Error on config", e)

            put_proccesed_image_into_sub_today_folder(latest_image, root_result_path)
            check_time_to_move_unprocessed_files(images_directory)
            return success, result

        except Exception as e:
            false, result = failed_processing_result(image_context)
            error = FLS_ERR_ImageProcessingFailed
            errordescription = f"{error_context.get_error_string(FLS_ERR_ImageProcessingFailed)}: {str(e)}"
            error_context.log_error()
            ErrorLogger.exception("Image processing failed due to an exception.")
            false, result = failed_processing_result(image_context)
            return false, result
    else:
        false, result = failed_processing_result(image_context)
        error_context.error = FLS_ERR_NoUnprocessedImage
        error_context.errordescription = error_context.get_error_string(FLS_ERR_NoUnprocessedImage)
        error_context.log_error()
        return false, result


def get_cleaned_path(section, key):
    """Retrieve a cleaned path value from the config file."""
    value = config.get(section, key).strip().strip("'").strip('"')
    return Path(value)

def stringfy_struct(data_struct):
    """
    Converts the attributes of a data structure to a formatted string.
    """
    return "\n".join(f"{attribute}: {value}" for attribute, value in data_struct.__dict__.items())

def save_view_as_image(image, vertical_lines, view, sp_values, num_tracks, result_dir):
    
    global horizontal_lines, horizontal_lines_colors, horizontal_lines_names
    # Convert the image to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)

    # Checking where to limit by num of tracks
    horizontal_lines = [value / 10000 for value in sp_values][:num_tracks]
    horizontal_lines_colors = ['blue'] * num_tracks
    horizontal_lines_names = [str(i + 1) for i in range(num_tracks)]


    # Create a figure for the matplotlib plot
    fig, ax = plt.subplots()
    ax.imshow(image_pil)
    ax.set_xticks([0, 200, 400, 600, 800, 1000])
    ax.set_xticklabels(['0', '0.2', '0.4', '0.6', '0.8', '1'])
    ax.set_yticks([0, 200, 400, 600, 800, 1000])
    ax.set_yticklabels(['0', '0.2', '0.4', '0.6', '0.8', '1'])
    ax.set_xlim(0, 1000)
    ax.set_ylim(1000, 0)  # Inverted y-axis
    ax.xaxis.set_ticks_position('top')
    ax.xaxis.set_label_position('top')
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Y-axis')
    #make that when calling get_latest_image function, it makes process, and data would be send back to c
    # Draw vertical lines
    for x in vertical_lines:
        ax.axvline(x=x, color='red', linestyle='-', linewidth=2)

    
    segment_width = vertical_lines[1] - vertical_lines[0]
    alert_shown = False
    for idx, (y, color, name) in enumerate(zip(horizontal_lines,horizontal_lines_colors,horizontal_lines_names)):
        y_pos = int(y * 1000)  # Scale normalized value to image dimension

        # Determine start and end x positions for the horizontal lines safely
        start_x = vertical_lines[idx - 1] if idx > 0 and idx - 1 < len(vertical_lines) else 0
        end_x = vertical_lines[idx] if idx < len(vertical_lines) else 1000

        ax.plot([start_x, end_x], [y_pos, y_pos], color=color, linewidth=2)
        ax.text(start_x, y_pos, name, color=color, fontsize=10, ha='right')

        #current_language = get_current_language()
        ax.plot([start_x, end_x], [y_pos, y_pos], color=color, linewidth=2)
        ax.text(start_x, y_pos, name, color=color, fontsize=10, ha='right')
    # Save the plot
    create_folder_for_today(fig, view, result_dir)

    # Close the figure to free up memory
    plt.close(fig)

#function to sort data for each view
def sort_data_by_view(view, pb_buf_do_wic):
    for attr_name, attr_value in pb_buf_do_wic.__dict__.items():
        if view > 1:
            print("View Number", view)
            print(f"{attr_name}: {attr_value}")


def main():
     """
    try:
        run_gui()
    except Exception as e:
        print(f"Error in GUI: {e}")
        import traceback
        traceback.print_exc()  # Print full error stack trace
    
    parser = argparse.ArgumentParser(description='Process the latest image.')
    parser.add_argument('-l', '--latest', action='store_true', help='Process the latest unprocessed image')
    parser.add_argument('-x', '--loop', action='store_true', help='Continuously check and process images')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config_path_dir = get_config_path()
    config.read(config_path_dir)


    if 'Settings' in config and config.has_option('Settings', 'root_images'):
        image_directory = config.get('Settings', 'root_image')
        print(f"Image directory from config: {image_directory}")

        if args.latest:
            # Process the latest image
            latest_image = get_latest_image(image_directory)
            if latest_image:
                print(f"Processing latest image: {latest_image}")
                #process_image_with_multiple_sub_images(latest_image)

            else:
                print("No unprocessed image to process.")
        elif args.loop:
            # Enter an infinite loop to process images
            print("Entering infinite loop to process images...")
            loop_indefinitely_process_images(image_directory)
        else:
            run_gui()
            #loop_indefinitely_process_images(image_directory)
    else:
        print("No image directory or pipe path specified in the config file.")
"""
if __name__ == "__main__":
    main()