#ALL THE STUFF THAT BELONGS TO FLS.CFG FILE
import os
import sys
import configparser
from pathlib import Path

def get_config_path() -> str:
    """
    Returns the path to the config file, creating it if needed.
    - When frozen: config lives next to the .exe
    - When dev: config lives in ../../config relative to this file
    """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        config_dir = os.path.join(base_path, 'config')
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.abspath(os.path.join(base_path, '..', '..', 'config'))

    config_path = os.path.join(config_dir, 'fls.cfg')

    # Ensure the config directory exists (both frozen & dev)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    # Create default config if missing
    if not os.path.exists(config_path):
        print(f"Creating default config at: {config_path}")
        create_default_config_image_processing(config_path)

    return config_path


def get_cleaned_path(section, key):
    """Retrieve a cleaned path value from the config file."""
    config = configparser.ConfigParser()
    value = config.get(section, key).strip().strip("'").strip('"')
    return Path(value)


def get_config_path_image_processing():
    """Finds or creates the config file for image processing."""
    
    if getattr(sys, 'frozen', False):  # If running as a PyInstaller bundle
        base_path = sys._MEIPASS
        config_dir = os.path.join(base_path, 'config')
    else:
        base_path = os.path.dirname(__file__)  # Development environment
        config_dir = os.path.abspath(os.path.join(base_path, '..', '..', 'config'))

    config_path = os.path.join(config_dir, 'fls.cfg')

    # Create config directory only in development mode
    if not getattr(sys, 'frozen', False):
        os.makedirs(config_dir, exist_ok=True)

    # Check if the config file exists; if not, create a default one
    if not os.path.exists(config_path):
        print("Creating default config file...")
        create_default_config_image_processing(config_path)

    return config_path

def create_default_config_image_processing(config_path):
    config = configparser.ConfigParser()


    config['Header'] = {
        'version': 'v2025.1.0a',
        'description': 'FLS configuration file',
        'updated_at': '2025-07-22',
        'updated_by': 'Pijus Marijus Mankus',
        'os': 'win64'
    }

    config['Settings'] = {
        'locale': 'en-UK',
        'number_of_tracks': '5',
        'root_image': r'C:\Users\tgdev01\Documents\GitHub\fls\img',
        'root_archive': r'C:\Users\tgdev01\Documents\GitHub\fls\img'

    }

    config['Selected_Views'] = {}

    # Write the configuration file to the specified path
    with open(config_path, 'w') as configfile:
        config.write(configfile)