import configparser
import ctypes
from ctypes import c_uint16
from core.rename import FileReader
import glob
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import traceback
from PIL import Image, ImageTk, ImageChops
import re
import os
from datetime import datetime, date
import sys
import cv2
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import get_config_path
from core import image_processor
from matplotlib import pyplot as plt, image as mpimg
from tkcalendar import DateEntry
from pathlib import Path
from fls_cli.fls_cli import get_fls_config
from profibus import CIFX70E_DP
import json
config = configparser.ConfigParser()
config_path = get_config_path()
config.read(config_path)
print("Config path", config_path)

image = None 

FLS_CALIBRATION_FILE_NAME = r"config/default_view_image.png"
LIVE_UPDATE_INTERVAL = 15000 
JSON_FILE_PATH = "../buffer_reads.json"
JSON_WRITE_FILE_PATH = "../buffer_writes.json"

class ImageContext:
    def __init__(self):
        self.data_read = None
        self.data_write = None


def get_cleaned_path(section, key):
    """Retrieve a cleaned path value from the config file."""
    value = config.get(section, key).strip().strip("'").strip('"')
    return Path(value)

# Try to read the config file and get paths
try:
    with open(config_path, 'r') as f:
        config.read_file(f)

    root_image_path = get_cleaned_path("Settings", "root_image")
    root_result_path = get_cleaned_path("Settings", "root_archive")
except FileNotFoundError:
    print(f"Error: Config file '{config_path}' not found. Using default directories.")
    root_image_path = Path("C:/")
    root_result_path = Path("C:/")
except configparser.Error as e:
    print(f"Error reading config file: {e}. Using default directories.")
    root_image_path = Path("C:/")
    root_result_path = Path("C:/")

# Ensure root directory exists
if not root_image_path.exists():
    print(f"Warning: Root directory '{root_image_path}' does not exist. Using default 'C:/' instead.")
    root_image_path = Path("C:")

# Dynamically create today's subfolder
today = datetime.now().strftime('%Y-%m-%d')
today_subfolder = root_image_path

# Ensure the subfolder exists
if not today_subfolder.exists():
    print(f"Warning: Subfolder '{today_subfolder}' does not exist.")

# Logfile path inside today's subfolder
logfile_path = today_subfolder / f'logfile_{today}.log'
default_log_path_today = today_subfolder / f'logfile_{today}.log'

# Fallback to a default log file within root_image if today's log file does not exist
fallback_logfile_path = root_image_path / 'fallback.log'

if not logfile_path.is_file():
    print(f"Warning: Log file '{logfile_path}' does not exist or is not a file.")
    if fallback_logfile_path.exists():
        logfile_path = fallback_logfile_path
        print(f"Using fallback log file: {logfile_path}")
    else:
        logfile_path = None
        print("No valid log file found. Skipping log file load.")


""" For further asistance 
logfile_path =  None
default_log_path_today = None

logfile_candidates = list(today_subfolder.glob("logfile_*.log")) if today_subfolder.exists() else []
if logfile_candidates:
    logfile_path = logfile_candidates[0]
    default_log_path_today = logfile_path
    print(f"Using today's logifle: {logfile_path}")

else:
    all_logfiles = sorted(
        root_image_path.glob("*/logfile_*.log"),
        key = lambda f: f.stat().st_mtime,
        reverse= True
    )
    if all_logfiles:
        logfile_path = all_logfiles[0]
        default_log_path_today = logfile_path
        print(f" Using fallback logifle from other folder: {logfile_path}")
    else:
        fallback_logfile_path = root_image_path / 'fallback.log'
        if fallback_logfile_path.exists():
            logfile_path = fallback_logfile_path
            default_log_path_today = fallback_logfile_path
            print(f"Using fallback log file : {logfile_path}")
        else:
            logfile_path = None
            default_log_path_today = None
            print("No valid log file found. Skiping log file load.")
"""

# Function to load the log file and return headers and entries
def load_logfile(filepath):
    headers = ['Timestamp', 'Tracks', 'Operator_setpoints', 'Processed_values', 'PV_quality', 'Image_name', 'View_name']
    log_entries = []

    if not filepath or not os.path.isfile(filepath):
        print(f"Logfile not found or invalid: {filepath}")
        return headers, log_entries

    with open(filepath, 'r') as file:
        lines = file.readlines()
        for line in lines[1:]:  # Skip the header line
            if line.strip():  # Skip empty lines
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) == len(headers):
                    log_entry = dict(zip(headers, parts))
                    log_entries.append(log_entry)
    return headers, log_entries


class LogfileViewerApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.sp_entries = []

        self.pv_entries = []

        self.current_state1_file1 = None
        self.current_state1_file2 = None

        if today_subfolder.exists():
            self.current_image_folder = today_subfolder
        else:
            self.current_image_folder = root_image_path

        # Load the log file first to initialize headers and log entries
        self.headers, self.log_entries = load_logfile(logfile_path)

        reader = FileReader(logfile_path)

        self.cwd_label_var = tk.StringVar()
        self.cwd_label_var.set(f" {str(self.current_image_folder)}")

        self.live_view_enabled = False  # Variable to track if live view is enabled

        self.pack(fill='both', expand=True, padx=10, pady=10)

        self.show_config_button = "--config" in sys.argv

        # Create UI elements
        self.create_widgets()
        update_live_interval_from_profibus()
        self.refresh_live_view_label()
        self.read_json_file()

        # Display log entries based on current date and time
        self.set_default_filters()
        self.filter_log_entries()
        self.populate_latest_valid_data(self.log_entries)

        

    

    def create_widgets(self):
        # Create a frame for the Treeview and image display

        #style = ttk.Style()
        #style.configure("BW.TLabel", background="red")

        filter_frame_top = ttk.Frame(self)
        filter_frame_top.pack(side=tk.TOP,fill=tk.X, expand=False, padx=10, pady=3)

        content_frame = ttk.Frame(self)
        #content_frame.pack(fill='both', expand=True)
        content_frame.pack(fill=tk.X, expand=False, padx=0, anchor='n')

        filter_path_frame = ttk.Frame(self)
        filter_path_frame.pack(side=tk.TOP,fill=tk.X, expand=False, padx=10, pady=3)


        view_frame = ttk.Frame(self)
        view_frame.pack(side=tk.TOP, fill=tk.X, padx=10)

        view_original_frame = ttk.Frame(view_frame)
        view_original_frame.pack(anchor='w', pady=(10, 0))

        timestamp_frame = ttk.Frame(self)
        timestamp_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False, padx=10, pady=3)
        


        # container for 2 image views
        #image_container = ttk.Frame(right_side_frame)
       # image_container.pack(anchor="n", pady=(10, 0))

        ttk.Label(filter_frame_top, text="Filter", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=2)

        ttk.Label(filter_frame_top, text="Start:", font=("Segoe UI", 10, "italic")).pack(side=tk.LEFT, padx=(16,2))

        self.start_date_entry = DateEntry(
            filter_frame_top,
            width=10,
            background='lightgreen',
            foreground='black',
            borderwidth=1,
            date_pattern='yyyy-mm-dd'
        )
        self.start_date_entry.pack(side=tk.LEFT, padx=2)

        #ttk.Label(filter_frame_top, text="Date").grid(row=1, column=2, sticky="w", padx=(0,0))
        #ttk.Label(filter_frame_top, text="Hour").grid(row=1, column=3, sticky="w", padx=(5,0))
        #ttk.Label(filter_frame_top, text="Minute").grid(row=1, column=4, sticky="w", padx=(0,0))

        self.start_hour_combobox = ttk.Combobox(filter_frame_top, values=[f"{i:02}" for i in range(24)], width=5)
        self.start_hour_combobox.pack(side=tk.LEFT, padx=2)
        self.start_hour_combobox.set("00")

        self.start_minute_combobox = ttk.Combobox(filter_frame_top, values=[f"{i:02}" for i in range(60)], width=5)
        self.start_minute_combobox.pack(side=tk.LEFT, padx=2)
        self.start_minute_combobox.set("00")

        # --- ROW 2: End Date/Time ---
        ttk.Label(filter_frame_top, text="End:", font=("Segoe UI", 10, "italic")).pack(side=tk.LEFT, padx=(8,2))
        current_datetime_button = ttk.Button(filter_frame_top, text="Now", width=5, command=self.set_to_current_datetime)
        current_datetime_button.pack(side=tk.LEFT, padx=2)

        self.end_date_entry = DateEntry(
            filter_frame_top,
            width=10,
            background='lightgreen',
            foreground='black',
            borderwidth=1,
            date_pattern='yyyy-mm-dd'
        )
        self.end_date_entry.pack(side=tk.LEFT, padx=2)

        self.end_hour_combobox = ttk.Combobox(filter_frame_top, values=[f"{i:02}" for i in range(24)], width=5)
        self.end_hour_combobox.set("23")
        self.end_hour_combobox.pack(side=tk.LEFT, padx=2)

        self.end_minute_combobox = ttk.Combobox(filter_frame_top, values=[f"{i:02}" for i in range(60)], width=5)
        self.end_minute_combobox.set("59")
        self.end_minute_combobox.pack(side=tk.LEFT, padx=2)




        # Buttons: Filter, Reset, Set to Current Date/Time
        filter_button = ttk.Button(filter_frame_top, text="Apply", command=self.filter_log_entries)
        filter_button.pack(side=tk.LEFT, padx=(8,2))

        #reset_button = ttk.Button(filter_frame, text="See whole pictures", command=self.reset_filters)
        #reset_button.grid(row=3, column=3, columnspan=2, pady=5)


        # Live View Toggle
        self.live_view_var = tk.BooleanVar()
        self.live_view_checkbox = ttk.Checkbutton(filter_path_frame, text=f"Live View {int(LIVE_UPDATE_INTERVAL / 1000)} sec", variable=self.live_view_var, command=self.toggle_live_view)
        #live_view_checkbox.grid(row=2, column=0, columnspan=1, pady=5)
        self.live_view_checkbox.pack(side=tk.LEFT, padx=2)

        self.label_file1 = tk.Label(filter_frame_top, text="Read state1:", font=("Arial", 12))
        self.label_file1.pack(side=tk.LEFT, padx=2)

        self.label_file2 = tk.Label(filter_frame_top, text="Write state1:", font=("Arial", 12))
        self.label_file2.pack(side=tk.LEFT, padx=2)



        reset_folder_button = ttk.Button(filter_path_frame, text="Image Root",command=self.reset_default_folder)
        reset_folder_button.pack(side=tk.LEFT, padx=2)


        # Button to choose folder

        choose_folder_button = ttk.Button(filter_path_frame, text="Choose Folder", command=self.choose_folder)
        choose_folder_button.pack(side=tk.LEFT, padx=2)


        cwd_label = ttk.Label(filter_path_frame, textvariable=self.cwd_label_var, foreground="black", font=("Segoe UI", 10, "italic"))
        cwd_label.pack(side=tk.LEFT, padx=2)


        #Display and Change setpoints

        #ttk.Label(filter_frame, text="Sp1:").grid(row=4, column=5, padx=(2, 0), sticky="e")
        #self.

        style = ttk.Style()
        style.configure("Blue.TLabel", foreground="blue")

        self.operator_values_var = tk.StringVar()
        self.tracks_var = tk.StringVar()
        self.process_values_var = tk.StringVar()

        #Setpoints
        self.sp_vars = [tk.StringVar() for _ in range(8)]
        #PV'S
        self.pv_vars = [tk.StringVar() for _ in range(8)]

        
        sp_label_frame = ttk.LabelFrame(view_frame, text="")
        #sp_label_frame.pack(anchor="n", pady=(0, 10))
        sp_label_frame.pack(side=tk.TOP, anchor="ne")
        

        
        self.image_label = ttk.Label(view_frame)
        self.image_label.pack(side=tk.RIGHT, anchor="ne", padx=0)

        self.image_label_original = ttk.Label(view_frame)
        self.image_label_original.pack(side=tk.RIGHT, padx=10)

        self.sp_label_widgets = []

        self.pv_label_widgets = []

        self.sp_title_label = None

        # Field and button instalisation for SP's
        for i in range(8):
            lbl = ttk.Label(sp_label_frame, text=f"{i+1}")
            lbl.grid(row = 0, column=i+1, padx=4, pady=(0,2))
            self.sp_label_widgets.append(lbl)

        for i in range(8):
            var = self.sp_vars[i]
            entry = tk.Entry(sp_label_frame, textvariable=var, width=6, fg="blue", relief="sunken", bg="#f3f3f3")
            entry.grid(row=1, column=i+1, padx=2, sticky="w")
            self.sp_entries.append(entry)
            entry.bind("<FocusIn>", lambda event, idx=i: self.on_entry_focus_in(idx))
            entry.bind("<FocusOut>", lambda event, idx=i: self.on_entry_focus_out(idx))

        
        #Field and button instalisation for PV's

        for i in range(8):
            pv_lbl = ttk.Label(sp_label_frame, text=f"{i+1}")
            pv_lbl.grid(row = 0, column=i+1, padx=4, pady=(0,2))
            self.pv_label_widgets.append(pv_lbl)

        for i in range(8):
            var = self.pv_vars[i]
            entry = tk.Entry(sp_label_frame, textvariable=var, width=6, fg="blue", relief="sunken", bg="#f3f3f3")
            entry.grid(row=2, column=i+1, padx=2, sticky="w")
            self.pv_entries.append(entry)
            entry.bind("<FocusIn>", lambda event, idx=i: self.on_entry_focus_in(idx))
            entry.bind("<FocusOut>", lambda event, idx=i: self.on_entry_focus_out(idx))

        
        self.label_timestamp1 = tk.Label(timestamp_frame, text="Timestamp Read:", font=("Arial", 10))
        self.label_timestamp1.pack(side=tk.LEFT, padx=2)

        self.label_timestamp2 = tk.Label(timestamp_frame, text="Timestamp Write:", font=("Arial", 10))
        self.label_timestamp2.pack(side=tk.LEFT, padx=2)
        # Create a Treeview for log entries with columns
        self.log_entries_frame = ttk.Frame(content_frame, padding="10")
        self.log_entries_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_entries_list = ttk.Treeview(self.log_entries_frame, show='headings')

        

        # Set up the columns and headings in the Treeview
        self.log_entries_list['columns'] = self.headers
        column_widths = { #sum 1300 +-
            'Timestamp': 120,
            'Tracks': 50,
            'Operator_setpoints': 250,
            'Processed_values': 250,
            'PV_quality': 250,
            'Image_name': 150,
            'View_name': 200
        }
        for header in self.headers:
            self.log_entries_list.heading(header, text=header)
            self.log_entries_list.column(header, width=column_widths.get(header, 150), anchor=tk.W)

        self.log_entries_list.pack(expand=True, fill=tk.BOTH)

        self.log_entries_list.bind("<<TreeviewSelect>>", self.on_treeview_select)

        self.log_entries_list.bind("<Button-1>", self.on_treeview_click)


        if self.show_config_button:

            ttk.Label(sp_label_frame, text="Submit", font=("Segoe UI", 9, "italic")).grid(row=0, column=0, padx=(9, 5), sticky="w")

            self.save_setpoints_button = ttk.Button(
                sp_label_frame,
                text="SP",
                command=self.apply_updated_setpoints,
                width = 5
            )
            self.save_setpoints_button.grid(row=1, column=0, padx=(8, 8), sticky="w")

            self.save_process_values_button = ttk.Button(
            sp_label_frame,
            text="PV",
            command=self.apply_written_pvs,
            width = 5
            )
            self.save_process_values_button.grid(row=2, column=0, padx=(8, 8), sticky="w")

            ttk.Label(filter_frame_top, text="Admin Panel", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(32,2))

            load_image_button = ttk.Button(filter_frame_top, text="Load Image", command=self.load_image)
            load_image_button.pack(side=tk.LEFT, padx=(16,8))

            config_button = ttk.Button(filter_frame_top, text="Config", command=self.open_config)
            config_button.pack(side=tk.LEFT, padx=(8,8))

    def choose_folder(self):
        global logfile_path

        # Open a dialog to select the folder
        folder_selected = filedialog.askdirectory()

        if folder_selected:
            for file_name in os.listdir(folder_selected):
                if file_name.endswith(".log"):
                    logfile_path = os.path.join(folder_selected, file_name)
                    self.current_image_folder = Path(folder_selected)
                    self.cwd_label_var.set(f" {folder_selected}")
                    break
            else:
                messagebox.showinfo("Info", "No .log file found in the selected folder.")
                return

            #load_logfile() is a function that loads the logfile data
            self.headers, self.log_entries = load_logfile(logfile_path)
            self.display_log_entries()
            self.reset_filters()
            self.populate_latest_valid_data(self.log_entries)
    
    def refresh_image(self):
        if hasattr(self.image_label, "image_path"):
            self.display_image(self.image_label.image_path)
            
    def display_image(self, image_path):
        # commented function is function for taking out white background
        img = auto_crop_image(image_path)
        #img = Image.open(image_path)
        img = img.resize((500, 500), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        self.image_label.config(image=photo)
        self.image_label.image = photo

        #self.image_label_original.config(image=photo)
        #self.image_label_original.image = photo

    def display_original_image(self, org_image_path):

        try:
            image = Image.open(org_image_path)
            img = image.resize((800, 450), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_label_original.config(image=photo)
            self.image_label_original.image = photo

        except Exception as e:
            print("An error occurred:", e)

    def set_default_filters(self):
        # Set the start and end dates and times to current date and time
        now = datetime.now()
        self.start_date_entry.set_date(now.date())
        self.end_date_entry.set_date(now.date())

    def set_to_current_datetime(self):
        # Update the filters
        now = datetime.now()
        self.start_date_entry.set_date(now.date())
        self.end_date_entry.set_date(now.date())
        self.start_hour_combobox.set("00")
        self.start_minute_combobox.set("00")
        self.end_hour_combobox.set(f"{now.hour:02}")
        self.end_minute_combobox.set(f"{now.minute:02}")
        self.filter_log_entries()
        self.populate_latest_valid_data()

    def reset_default_folder(self):
        global logfile_path, default_log_path_today

        today_folder = default_log_path_today.parent

        self.current_image_folder = root_image_path

        logfile_path = root_image_path

        """
        if today_folder.exists():
            self.current_image_folder = today_folder
            if default_log_path_today.exists():
                logfile_path = default_log_path_today
            else:
                logfile_path = None 
        else:
            self.current_image_folder = root_image_path
            logfile_path = None
            """
        # Load logfile
        if logfile_path and os.path.exists(logfile_path):
            self.headers, self.log_entries = load_logfile(logfile_path)
            self.display_log_entries()
            self.reset_filters()
            self.populate_latest_valid_data(self.log_entries)
        else:
            # Clear entries
            print("Log does not exists")
            self.headers, self.log_entries = None, None
            self.log_entries_list.delete(*self.log_entries_list.get_children())
        
        self.image_label.config(image="")
        self.image_label_original.config(image="")
        self.image_label.image = None
        if hasattr(self, "original_image"):
            del self.original_image

        self.cwd_label_var.set(f" {str(self.current_image_folder)}")
        for var in self.sp_vars:
            var.set("")
        self.populate_latest_valid_data(self.log_entries)
        
        

    def display_log_entries(self, entries=None):
        if entries is None:
            entries = self.log_entries

        self.log_entries_list.delete(*self.log_entries_list.get_children())
        for log_entry in entries:
            log_entry_values = [log_entry[header] for header in self.headers]
            self.log_entries_list.insert('', 'end', values=log_entry_values)

    def filter_log_entries(self):
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        start_hour = self.start_hour_combobox.get()
        start_minute = self.start_minute_combobox.get()
        end_hour = self.end_hour_combobox.get()
        end_minute = self.end_minute_combobox.get()

        try:
            start_time = datetime.strptime(f"{start_date} {start_hour}:{start_minute}:00", "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(f"{end_date} {end_hour}:{end_minute}:00", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please ensure all fields are filled correctly.")
            return

        filtered_entries = [
            entry for entry in self.log_entries
            if start_time <= datetime.strptime(entry['Timestamp'], "%Y-%m-%d %H:%M:%S") <= end_time
        ]

        self.display_log_entries(filtered_entries)
        self.populate_latest_valid_data(filtered_entries)

    def reset_filters(self):
        self.set_default_filters()
        self.display_log_entries()

    def toggle_live_view(self):
        """Toggle live view on or off."""
        if self.live_view_var.get():
        # Check if logs contain any operator setpoints
            has_setpoints = any(entry.get("Operator_setpoints", "").strip()
                                for entry in self.log_entries)

            if not has_setpoints:
                messagebox.showerror("Live View Disabled",
                                    "Cannot enable Live View: No operator setpoints found in logs.")
                self.live_view_var.set(False)
                return

            self.live_view_enabled = True
            # Disable editing on SP fields
            self.set_setpoints_editable(False)
            # Start live update cycle
            self.update_logfile_live()
        else:
            self.live_view_enabled = False

            # Enable editing on SP fields again
            self.set_setpoints_editable(True)

    def refresh_live_view_label(self):
        global LIVE_UPDATE_INTERVAL
        new_text = f"Live View {int(LIVE_UPDATE_INTERVAL / 1000)} sec"
        self.live_view_checkbox.config(text=new_text)

    def update_logfile_live(self):
        global LIVE_UPDATE_INTERVAL

        if not self.live_view_enabled:
            return

        # Reload the logfile
        try:
            self.headers, self.log_entries = load_logfile(logfile_path)
        except Exception as e:
            print(f"Failed to reload logfile: {e}")

        # Dynamically update interval
        update_live_interval_from_profibus()

        self.refresh_live_view_label()

        latest_entry = self.get_latest_log_entry_with_setpoints()
        if latest_entry:
            self.populate_latest_valid_data([latest_entry])
            self.display_log_entries(self.log_entries)
            self.update_image_view(latest_entry)
        else:
            self.populate_latest_valid_data([])

        if self.live_view_enabled:
            print(f"[GUI] Next update in {LIVE_UPDATE_INTERVAL} ms")
            self.after(LIVE_UPDATE_INTERVAL, self.update_logfile_live)

    
    def read_json_file(self):
        try:
            with open(JSON_FILE_PATH, "r") as file, open(JSON_WRITE_FILE_PATH, "r") as file2:
                read_data = json.load(file)
                write_data = json.load(file2)

            # Expecting dict not list:
            new_state1_file1 = read_data.get("state1") if isinstance(read_data, dict) else None
            if new_state1_file1 is None:
                print("Not getting Rfile state")

            if all(k in read_data for k in ["year", "month", "day", "hours", "minutes", "seconds"]):
                read_time = f'{read_data["year"]:04d}-{read_data["month"]:02d}-{read_data["day"]:02d} ' \
                            f'{read_data["hours"]:02d}:{read_data["minutes"]:02d}:{read_data["seconds"]:02d}'
                self.label_timestamp1.config(text=f"Read time: {read_time}")
            else:
                self.label_timestamp1.config(text="Read time: N/A")

            new_state1_file2 = write_data.get("state1") if isinstance(write_data, dict) else None
            if new_state1_file2 is None:
                print("Not getting Wfile state")

            if all(k in write_data for k in ["year", "month", "day", "hours", "minutes", "seconds"]):
                write_time = f'{write_data["year"]:04d}-{write_data["month"]:02d}-{write_data["day"]:02d} ' \
                            f'{write_data["hours"]:02d}:{write_data["minutes"]:02d}:{write_data["seconds"]:02d}'
                self.label_timestamp2.config(text=f"Write time: {write_time}")
            else:
                self.label_timestamp2.config(text="Write time: N/A")

            

            if new_state1_file1 != getattr(self, 'current_state1_file1', None):
                self.current_state1_file1 = new_state1_file1
                self.label_file1.config(text=f"Read state1: {hex(self.current_state1_file1)}")

            if new_state1_file2 != getattr(self, 'current_state1_file2', None):
                self.current_state1_file2 = new_state1_file2
                self.label_file2.config(text=f"Write state1: {hex(self.current_state1_file2)}")

        except Exception as e:
            print(f"Error reading JSON: {e}")

        self.after(2000, self.read_json_file)


    
    def update_info(self):

        if self.live_view_var.get():
        # Check if logs contain any operator setpoints
            has_setpoints = any(entry.get("Operator_setpoints", "").strip()
                                for entry in self.log_entries)
            if not has_setpoints:
                messagebox.showerror("Live View Disabled",
                                    "Cannot enable Live View: No operator setpoints found in logs.")
                self.live_view_var.set(False)
                return
        # Reload the logfile
            try:
                self.headers, self.log_entries = load_logfile(logfile_path)
            except Exception as e:
                print(f"Failed to reload logfile: {e}")
                return

            # Update GUI
            latest_entry = self.get_latest_log_entry_with_setpoints()
            if latest_entry:
                self.populate_latest_valid_data([latest_entry])
                self.display_log_entries(self.log_entries) 
                self.update_image_view(latest_entry)
            else:
                # No setpoints found yet, still update GUI with blanks
                self.populate_latest_valid_data([])

    def update_image_view(self, log_entry):
        """
        Display the image from the 'View_name' column in live view.
        """
        if "View_name" not in self.headers:
            print("View_name column not found in headers.")
            return

        image_name = log_entry.get("View_name")
        image_org = log_entry.get("Image_name")
        if not image_name:
            print("No View_name value in log entry.")
            return
        if not image_org:
            print("No Original Image value in log entry.")
            return
        
        root_result_path = Path(get_cleaned_path("Settings", "root_archive"))

        image_path = self.current_image_folder / image_name
        image_org_path = root_result_path / image_org

        if image_path.exists():
            self.image_label.image_path = image_path  # Optional, for refresh_image()
            self.display_image(image_path)
            self.display_original_image(image_org_path)
        else:
            print(f"Image not found at path: {image_path}")
    #configuration functions callers
    def load_image(self):
        load_image_conf()
    def open_config(self):
    # Config button 
        open_original_image(self.parent)
    
    def set_default_for_calendar(self):
        now_time = datetime.now()
        self.start_date_entry.set_date(date(2001,1,1))
        self.end_date_entry.set_date(now_time.date())
        self.start_hour_combobox.set("00")
        self.start_minute_combobox.set("00")
        self.end_hour_combobox.set("00")
        self.end_minute_combobox.set("00")
        self.filter_log_entries()
        
    
    def on_treeview_select(self, event):
        selected_item = self.log_entries_list.selection()
        if not selected_item:
            return

        item = self.log_entries_list.item(selected_item)
        log_entry_values = item["values"]

        self.selected_item_id = selected_item[0]

        num_tracks = 0

        if "Tracks" in self.headers:
            tracks_index = self.headers.index("Tracks")
            tracks_values = log_entry_values[tracks_index]
            self.tracks_var.set(tracks_values)

            self.headers

            try:
                num_tracks = int(tracks_values)
            except ValueError:
                num_tracks = 0

        if "Operator_setpoints" in self.headers:
            operator_index = self.headers.index("Operator_setpoints")
            process_value_index = self.headers.index("Processed_values")

            view_column_index = self.headers.index("View_name")
            image_name = log_entry_values[view_column_index]

            image_path = self.current_image_folder / image_name  #Use the current folder

            op_values = log_entry_values[operator_index]
            self.operator_values_var.set(op_values)

            pv_values = log_entry_values[process_value_index]
            self.process_values_var.set(pv_values)

            #split_values = re.split(r'[,\s;]+', op_values.strip())

            split_values = re.split(r'[,\s;]+', op_values)

            split_pv_values = re.split(r'[,\s;]+', pv_values)

            img_width = 545
            padding_px = 12
            total_padding = padding_px * num_tracks
            field_width_px = max((img_width - total_padding) // max(1, num_tracks), 40)

            char_width = max(int(field_width_px / 7), 4)


            """ OLDER VERSION
            split_values = re.split(r'[,\s;]+', op_values)
            for i in range(min(8, len(split_values))):
                self.sp_vars[i].set(split_values[i])
            
            split_values = re.split(r'[,\s;]+', op_values.strip())
            """

            
            for i in range(8):
                if i < num_tracks:
                    #sp
                    self.sp_vars[i].set(split_values[i] if i < len(split_values) else "")
                    self.sp_entries[i].config(width=char_width)
                    self.sp_entries[i].grid()                 # Show entry
                    self.sp_label_widgets[i].grid()           # Show SP label number
                    #pv
                    self.pv_vars[i].set(split_pv_values[i] if i < len(split_pv_values) else "")
                    self.pv_entries[i].config(width=char_width)
                    self.pv_entries[i].grid()
                    self.pv_label_widgets[i].grid()
                else:
                    self.sp_entries[i].grid_remove()          # Hide entry
                    self.sp_label_widgets[i].grid_remove()    # Hide SP label number
                    self.sp_vars[i].set("")
                    #pv
                    self.pv_entries[i].grid_remove()
                    self.pv_label_widgets[i].grid_remove()
                    self.pv_vars[i].set("")


        if "View_name" in self.headers:
            view_column_index = self.headers.index("View_name")
            image_name = log_entry_values[view_column_index]


            image_name_index = self.headers.index("Image_name")
            image_name_org = log_entry_values[image_name_index]



            image_path_org = os.path.join(self.current_image_folder, image_name_org)

            root_result_path = Path(get_cleaned_path("Settings", "root_archive"))
            image_path_org = root_result_path / image_name_org

            print("Root image_patj", image_path_org)


            image_path = self.current_image_folder / image_name  #Use the current folder

            if image_path_org.exists():
                self.display_original_image(image_path_org)
                self.selected_image_path = image_path_org
            else:
                self.image_label_original.config(image="") 
                print("Error", f"Image '{image_name_org}' not found in '{self.current_image_folder}'")

            if image_path.exists():
                self.display_image(image_path)
            else:
                self.image_label.config(image="") 
                messagebox.showerror("Error", f"Image '{image_name}' not found in '{self.current_image_folder}'")
    
    def on_treeview_click(self, event):
        row_id = self.log_entries_list.identify_row(event.y)
        if not row_id:
            self.log_entries_list.selection_remove(self.log_entries_list.selection())
            self.image_label.config(image="")  
            self.image_label_original.config(image="") 
            self.image_label.image = None
            self.image_label_original.image = None
            self.selected_image_path = None


    def populate_latest_operator_setpoints(self, entries=None):
        if not entries:
            entries = self.log_entries

        num_fields = 8  # default
        default_empty = True
        split_values = []

        if entries:
            for entry in reversed(entries):
                setpoints_str = entry.get("Operator_setpoints", "").strip()
                processed_str = entry.get("Processed_values", "").strip()
                tracks_str = entry.get("Tracks", "").strip()

                if setpoints_str:
                    split_values = re.split(r'[,\s;]+', setpoints_str)
                    split_processed_values = re.split(r'[,\s;]+', processed_str)

                    try:
                        num_fields = int(tracks_str)
                    except (ValueError, TypeError):
                        num_fields = len(split_values)
                        num_fields = len(split_processed_values)  # fallback based on actual data

                    default_empty = False
                    break

        # Ensure num_fields is between 1 and 8
        num_fields = max(1, min(num_fields, 8))

        # Show/hide fields and set values
        for i in range(8):
            if i < num_fields:
                self.sp_entries[i].grid()
                self.sp_label_widgets[i].grid()
                if not default_empty and i < len(split_values):
                    self.sp_vars[i].set(split_values[i])
                else:
                    self.sp_vars[i].set("")
            else:
                self.sp_entries[i].grid_remove()
                self.sp_label_widgets[i].grid_remove()

        self.set_setpoints_editable(not self.live_view_enabled)

    def populate_latest_valid_data(self, entries=None):
        if not entries:
            entries = self.log_entries

        num_fields = 8  # default
        default_empty = True
        split_values = []

        if entries:
            for entry in reversed(entries):
                setpoints_str = entry.get("Operator_setpoints", "").strip()
                processed_str = entry.get("Processed_values", "").strip()
                
                tracks_str = entry.get("Tracks", "").strip()

                if setpoints_str and processed_str:
                    split_values = re.split(r'[,\s;]+', setpoints_str)
                    split_processed_values =  re.split(r'[,\s;]+', processed_str)

                    try:
                        num_fields = int(tracks_str)
                    except (ValueError, TypeError):
                        num_fields = len(split_values)
                        num_fields = len(split_processed_values)  # fallback based on actual data

                    default_empty = False
                    break

        # Ensure num_fields is between 1 and 8
        num_fields = max(1, min(num_fields, 8))

        # Show/hide fields and set values
        for i in range(8):
            if i < num_fields:
                self.sp_entries[i].grid()
                self.sp_label_widgets[i].grid()
                self.pv_entries[i].grid()
                self.pv_label_widgets[i].grid()
                if not default_empty and i < len(split_values):
                    self.sp_vars[i].set(split_values[i])
                    self.pv_vars[i].set(split_processed_values[i])
                else:
                    self.sp_vars[i].set("")
                    self.pv_vars[i].set("")
            else:
                self.sp_entries[i].grid_remove()
                self.sp_label_widgets[i].grid_remove()
                self.pv_entries[i].grid_remove()
                self.pv_label_widgets[i].grid_remove()

        self.set_setpoints_editable(not self.live_view_enabled)


    def get_latest_log_entry_with_setpoints(self):
        if not self.log_entries:
            return None  # Gracefully handle None or empty list

        for entry in reversed(self.log_entries):  # iterate from latest to oldest
            if entry.get("Operator_setpoints", "").strip() or entry.get("Processed_values", "").strip():
                return entry
        return None

    def apply_updated_setpoints(self):
        #updated_values = [var.get().strip() for var in self.sp_vars]
        TRACKS_PER_VIEW_MAX = 8
        updated_values = []
        for var in self.sp_vars:
            val = var.get().strip()
            updated_values.append(val)

        if not hasattr(self, "selected_image_path") or self.selected_image_path is None:
            messagebox.showwarning("No Image", "No image selected or image not found.")
            print("DEBUG: selected_image_path =", getattr(self, "selected_image_path", "Attribute not set"))
            return
    
        if hasattr(self, "selected_item_id"):
            # Populate GUI view
            combined_setpoints = ','.join(updated_values)
            self.log_entries_list.set(self.selected_item_id, column="Operator_setpoints", value=combined_setpoints)

            if today_subfolder.exists():
                default_directory = today_subfolder
            else:
                default_directory = root_image_path

            # Populate sim_cntx for simulation or processing
            sim_cntx = ImageContext()
            sim_cntx.data_read = CIFX70E_DP.PbBufInWic()

            # Only update sp1; convert values and handle empty input
            sp_values = []
            for val in updated_values:
                try:
                    sp_values.append(int(float(val) * 10000))  
                except ValueError:
                    sp_values.append(0)

            # match TRACKS_PER_VIEW_MAX
            sp_values = (sp_values + [0] * TRACKS_PER_VIEW_MAX)[:TRACKS_PER_VIEW_MAX]
            sim_cntx.data_read.sp1[:] = sp_values

            image_processor.update_pb_in_struct(sim_cntx)
            CIFX70E_DP.WIC_PrintPBStruct(sim_cntx.data_read)

            rerun_image_processing(
                picked_image=self.selected_image_path,
                images_directory=default_directory, sim_cntx=sim_cntx
            )

            #image.show()
            self.update_info()
        else:
            messagebox.showwarning("No Selection", "Please select a log row to apply setpoints to.")

    def apply_written_pvs(self):
        TRACKS_PER_VIEW_MAX = 8
        updated_pv_values = []
        updated_sp_values = []
        for var in self.pv_vars:
            val = var.get().strip()
            updated_pv_values.append(val)

        for var in self.sp_vars:
            val = var.get().strip()
            updated_sp_values.append(val)

        if not hasattr(self, "selected_image_path") or self.selected_image_path is None:
            messagebox.showwarning("No Image", "No image selected or image not found.")
            print("DEBUG: selected_image_path =", getattr(self, "selected_image_path", "Attribute not set"))
            return

        if hasattr(self, "selected_item_id"):
            if today_subfolder.exists():
                default_directory = today_subfolder
            else:
                default_directory = root_image_path

            
            sim_cntx = ImageContext()
            sim_cntx.data_write = CIFX70E_DP.PbBufOutWic()
            sim_cntx.data_read = CIFX70E_DP.PbBufInWic()

            # Convert PV values
            pv_values = []
            sp_values = []
            for val in updated_pv_values:
                try:
                    pv_values.append(int(float(val) * 10000))
                except ValueError:
                    pv_values.append(0)
            for val in updated_sp_values:
                try:
                    sp_values.append(int(float(val) * 10000))
                except ValueError:
                    sp_values.append(0)

            pv_values = (pv_values + [0] * TRACKS_PER_VIEW_MAX)[:TRACKS_PER_VIEW_MAX]
            sim_cntx.data_write.pv1[:] = pv_values

            sp_values = (sp_values + [0] * TRACKS_PER_VIEW_MAX)[:TRACKS_PER_VIEW_MAX]
            sim_cntx.data_read.sp1[:] = sp_values
            image_processor.update_pb_in_struct(sim_cntx)
            image_processor.update_pb_do_struct(sim_cntx)
            CIFX70E_DP.print_PbBufOutWic(sim_cntx.data_write)

            #sim_cntx_read,old_sim_cntx, sim_cntx_write,picked_image_path, result_dir

            
            image_processor.reprocess_after_manually_pv_injection(
            sim_cntx.data_read,
            sim_cntx.data_write,
            picked_image_path=self.selected_image_path,
            result_dir=default_directory,
            )

            time.sleep(2)
            self.update_info()

        else:
            messagebox.showwarning("No Selection", "Please select a log row to apply PVs to.")




    def set_setpoints_editable(self, editable: bool):
        """Enable or disable the SP entry fields."""
        state = "normal" if editable else "disabled"
        for entry in self.sp_entries:
            entry.config(state=state)
        for entry in self.pv_entries:
            entry.config(state=state)

    def on_entry_focus_in(self, index):
        """Change background to red when entry is clicked."""
        self.sp_entries[index].config(bg="white")
        self.pv_entries[index].config(bg="white")

    def on_entry_focus_out(self, index):
        """Reset background when user clicks away."""
        self.sp_entries[index].config(bg="#f3f3f3")
        self.pv_entries[index].config(bg="#f3f3f3")




def get_latest_image(directory):
    all_png_files = glob.glob(os.path.join(directory, '*.png'))

    if not all_png_files:
        print(f"No .png files found in {directory}")
        return None

    # Filter out any images that have already been processed
    unprocessed_files = [img for img in all_png_files if '*' not in os.path.basename(img)]

    if not unprocessed_files:
        print(f"No unprocessed .png files found in {directory}")
        return None

    # Return the latest unprocessed image based on modification/creation time
    latest_unprocessed_image = max(unprocessed_files, key=os.path.getctime)
    return latest_unprocessed_image

# TO USE FOR TAKING OUT WHITE BACKGROUND FROM VIEW IMAGE

def auto_crop_image(image_path):
    img = Image.open(image_path).convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))

    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()

    if bbox:
        left, upper, right, lower = bbox

        # expand cropped place
        right = min(right + 10, img.width)
        lower = min(lower + 20, img.height)

        cropped_img = img.crop((left, upper, right, lower))
        return cropped_img
    else:
        return img  # fallback if no bounding box is found


def update_live_interval_from_profibus():
    """
    Read interval1 from Profibus and update LIVE_UPDATE_INTERVAL.
    """
    global LIVE_UPDATE_INTERVAL

    config = get_fls_config()
    board = config["szBoard"]
    firmware_path = config["szFirmwareFile"]
    timeout = config["ulIOTimeout"]

    CIFXHANDLE = ctypes.c_void_p
    hDriver = CIFXHANDLE(None)
    #make  fls_cli run with arg img, sp1 or sp2 or other sp to run image process 
    # Open the driver
    if CIFX70E_DP.wic_dll.xDriverOpen(ctypes.byref(hDriver)) != CIFX70E_DP.CIFX_NO_ERROR:
        print("Failed to open cifX70e driver,can only operate on simulation mode")
        pass
        sys.exit(1)
    else:

        slave = CIFX70E_DP.FLS_ReadSingleIOData(hDriver, board, timeout)

        if slave:
            new_interval = max(1000, slave.interval1 * 1000)
            if new_interval != LIVE_UPDATE_INTERVAL:
                print(f"[Profibus] Updating LIVE_UPDATE_INTERVAL from {LIVE_UPDATE_INTERVAL} → {new_interval}")
                LIVE_UPDATE_INTERVAL = new_interval
        else:
            print("[Profibus] Failed to read interval1.")
    
def run_simulated_data(picked_image, images_directory):
    config = get_fls_config()
    board = config["szBoard"]
    firmware_path = config["szFirmwareFile"]
    timeout = config["ulIOTimeout"]

    sim_cntx = ImageContext()


    CIFXHANDLE = ctypes.c_void_p
    hDriver = CIFXHANDLE(None)
    #make  fls_cli run with arg img, sp1 or sp2 or other sp to run image process 
    # Open the driver
    if CIFX70E_DP.wic_dll.xDriverOpen(ctypes.byref(hDriver)) != CIFX70E_DP.CIFX_NO_ERROR:
        print("Failed to open cifX70e driver,can only operate on simulation mode")
        pass
        sys.exit(1)
    else:
        #fls_run(board, timeout, hDriver, image_path=Image_Config_Path)
        #print("cifX70e driver is open.")
        try:

            sim_cntx.data_read = CIFX70E_DP.FLS_ReadSingleIOData(hDriver, board, timeout)

            if not sim_cntx or not sim_cntx.data_read:
                print("There is no processed image to take context")
                return None
            
            image_processor.update_pb_in_struct(sim_cntx)
            success, result = image_processor.process_image_with_multiple_sub_images(sim_cntx, picked_image, images_directory, create_log='No', manually='Yes')

            if success and result:
                print("Simulate Processing succeeded. Result:", result)
                #pprint.pprint(image_context)
            else:
                print("Simulatation failed. Check logfile.")
                sys.exit(1)

            # 3. Write operation
            print("\n--- Write Data ---")
            if success and result:
                #CIFX70E_DP.WIC_SendToMaster(hDriver, board, timeout, result)
                print("Write Operation Completed.")
            else:
                print("Write operation skipped due to processing failure.")

        except Exception as e:
            print(f"An error occurred Now: {e}")
            return

        finally:
            print("Succeded")
            print(f"Board: {board}, Firmware: {firmware_path}, Timeout: {timeout}")
            if hDriver:
                CIFX70E_DP.wic_dll.xDriverClose(hDriver)
                print("cifX70e driver closed.")
         
def rerun_image_processing(picked_image, images_directory, sim_cntx=None):
    if sim_cntx is None:
        print("Error: sim_cntx with setpoint not provided")

    try:
        image_processor.update_pb_in_struct(sim_cntx)

        success, result = image_processor.process_image_with_multiple_sub_images(
            sim_cntx,
            picked_image,
            images_directory,
            create_log='No',
            manually='Yes'
        )

        if success and result:
            print("Simulated Processing succeeded. Result:", result)
        else:
            print("Simulation failed. Check log output.")

    except Exception as e:
        print(f"An error occurred during image processing: {e}")



def rerun_image_processing_pv(picked_image, images_directory, sim_cntx=None):
    if sim_cntx is None:
        print("Error: sim_cntx with setpoint not provided")

    try:
        image_processor.update_pb_do_struct(sim_cntx)

        success, result = image_processor.process_image_with_multiple_sub_images(
            sim_cntx,
            picked_image,
            images_directory,
            create_log='No',
            manually='Yes'
        )

        if success and result:
            print("Simulated Processing succeeded. Result:", result)
        else:
            print("Simulation failed. Check log output.")

    except Exception as e:
        print(f"An error occurred during image processing: {e}")
# Function to open a View coniguration

def get_test_image_path():
    path = Path(__file__).resolve().parent.parent.parent / FLS_CALIBRATION_FILE_NAME
    if not path.exists():
        print(f"Warning: Test image not found at {path}")
    return path


def load_image_conf():
    global image
    file_path = filedialog.askopenfilename()
    if not file_path:
        return

    image = cv2.imread(file_path)
    messagebox.showinfo("Info", "Image loaded successfully, now you can configure the view")

def open_original_image(window,image_folder=None):
    global image

    
    try:
        # If image is already loaded
        if image is None:
            folder_to_use = image_folder or getattr(window, 'current_image_folder', None)

            if folder_to_use:
                print(f"Checking for latest image in: {folder_to_use}")
                latest = get_latest_image(folder_to_use)
                if latest and latest.exists():
                    image = cv2.imread(str(latest))
                    print(f"Loaded latest image from folder: {latest.name}")

            # test image
            if image is None:
                print("No valid latest image found. Checking for test image.")
                test_image = get_test_image_path()
                if test_image and test_image.exists():
                    image = cv2.imread(str(test_image))
                    print(f"Loaded fallback test image: {test_image.name}")

        if image is None:
            raise FileNotFoundError("No image loaded, found in folder, or as fallback.")

    except Exception as e:
        messagebox.showerror("Error", f"Could not open image.\n{str(e)}")
        return  # Make sure not to go further if loading fails
        
    if image is not None:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        photo = Image.fromarray(image_rgb)

        # Get the screen width and height
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Calculate the scale factor
        max_image_width = int(screen_width * 0.9)  # 90% of screen width
        max_image_height = int(screen_height * 0.8)  # 80% of screen heigh

        # Scale image to fit
        scale_factor = min(max_image_width / photo.width, max_image_height / photo.height, 1)

    
        new_width = int(photo.width * scale_factor)
        new_height = int(photo.height * scale_factor)

        
        resized_photo = photo.resize((new_width, new_height))
        resized_photo_tk = ImageTk.PhotoImage(resized_photo)

        # Set up the window
        window_original_image = tk.Toplevel()
        window_original_image.title("FLS View Picker (v2025.1.0a)")

        x_offset = (screen_width - new_width) // 2
        y_offset = (screen_height - new_height) // 4
        window_original_image.geometry(f"{new_width}x{new_height + 100}+{x_offset}+{y_offset}")

        canvas = tk.Canvas(window_original_image, width=new_width, height=new_height, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=resized_photo_tk)

        # Allow window to be resizable
        window_original_image.resizable(False, False)

        # Keep a reference of the resized photo to prevent garbage collection
        label_original_image = tk.Label(window_original_image, image=resized_photo_tk)
        label_original_image.image = resized_photo_tk

        # Add cropping functionality
        views = []
        current_view = None
        selected_view_index = None  # To keep track of which view is selected
        adding_view = False  # Variable to toggle "Add View" mode

        # Check if the config file exists and set the default view if not present
        config.read('fls.cfg')
        if 'Selected_Views' not in config or not config.options('Selected_Views'):
            if 'Selected_Views' not in config:
                config.add_section('Selected_Views')

            # Set the full image as the default view
            default_view = [0, 0, photo.width, photo.height]
            config.set('Selected_Views', 'View_1', str(default_view))

            with open('fls.cfg', 'w') as configfile:
                config.write(configfile)

        # Load the views from the configuration file
        for i in range(len(config.options('Selected_Views'))):
            view_str = config.get('Selected_Views', f'View_{i + 1}')
            view = list(map(int, view_str[1:-1].split(', ')))
            view_scaled = [int(x * new_width / photo.width) for x in view[:2]] + [int(y * new_height / photo.height)
                                                                                  for y in view[2:]]
            views.append(view_scaled)

        # Draw the views on the canvas
        for i, view in enumerate(views):
            canvas.create_rectangle(view[0], view[1], view[2], view[3], outline="blue", tags="view")
            canvas.create_text(view[0], view[1], text=f"View {i + 1}", anchor=tk.NW, fill="blue", tags="view_label")

        def is_inside_view(x, y, view):
            return view[0] <= x <= view[2] and view[1] <= y <= view[3]

        def on_button_press(event):
            nonlocal current_view, selected_view_index, adding_view
            if adding_view:
                if len(views) < 4:  # Limit the number of views to 4
                    current_view = [event.x, event.y, event.x, event.y]
                    views.append(current_view)
                    selected_view_index = len(views) - 1
                    redraw_views()
                    adding_view = False  # Turn off "Add View" mode after one view is added
                else:
                    messagebox.showinfo("Limit Reached", "You can only add a maximum of 4 views.")
            else:
                for i, view in enumerate(views):
                    if is_inside_view(event.x, event.y, view):
                        selected_view_index = i
                        current_view = view
                        return

        def on_mouse_drag(event):
            nonlocal current_view
            if current_view:
                current_view[2] = event.x
                current_view[3] = event.y
                redraw_views()

        def on_button_release(event):
            nonlocal current_view
            if current_view:
                current_view = None

        def redraw_views():
            # Clear all views and labels (views and their corresponding text labels)
            canvas.delete("view")
            canvas.delete("view_label")

            for i, view in enumerate(views):
                color = "green" if i == selected_view_index else "blue"
                canvas.create_rectangle(view[0], view[1], view[2], view[3], outline=color, tags="view")
                canvas.create_text(view[0], view[1], text=f"View {i + 1}", anchor=tk.NW, fill=color, tags="view_label")

        def reset_to_default():
            nonlocal views, current_view, selected_view_index
            views.clear()  # Clear all selected views
            current_view = None
            selected_view_index = None

            # Create a view that spans the entire image
            full_image_view = [0, 0, new_width, new_height]  # View that covers the entire image
            views.append(full_image_view)  # Add this as the only view
            selected_view_index = 0  # Select the full image view

            canvas.delete("all")  # Clear the canvas
            canvas.create_image(0, 0, anchor=tk.NW, image=resized_photo_tk)  # Redraw the entire image
            redraw_views()  # Redraw the views

        def undo_last_view():
            nonlocal views, selected_view_index
            if views:
                views.pop()  # Remove the last view
                selected_view_index = None
                redraw_views()  # Redraw the remaining views and their labels

        def close_window():
            window_original_image.destroy()

        def crop_views():
            if len(views) == 0:
                messagebox.showwarning("No Views", "Please draw views first.")
                return

            with open('fls.cfg', 'w') as configfile:
                config.write(configfile)
            config.read('fls.cfg')

            if 'Selected_Views' not in config:
                config.add_section('Selected_Views')

            # Remove excess views from config file
            for i in range(len(views), len(config.options('Selected_Views'))):
                config.remove_option('Selected_Views', f'View_{i + 1}')

            for i, view in enumerate(views):
                x1, y1, x2, y2 = map(int, view)
                crop_view = (
                    int(x1 * photo.width / new_width),
                    int(y1 * photo.height / new_height),
                    int(x2 * photo.width / new_width),
                    int(y2 * photo.height / new_height)
                )

                cropped_image = photo.crop(crop_view)
                # cropped_image.save(f"cropped_view_{i + 1}.png")

                config.set('Selected_Views', f'View_{i + 1}', str(crop_view))

            with open('fls.cfg', 'w') as configfile:
                config.write(configfile)

            messagebox.showinfo("Success",
                                f"Selected {len(views)} saved to fls.cfg")

        # Function to activate "Add View" mode
        def add_view():
            nonlocal adding_view
            if len(views) < 4:
                adding_view = True
                messagebox.showinfo("Add View", "Click on the image to add a new view.")
            else:
                messagebox.showinfo("Limit Reached", "You can only add a maximum of 4 views.")

        # Bind canvas events
        canvas.bind("<ButtonPress-1>", on_button_press)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_button_release)

        # Frame for organizing buttons horizontally at the bottom
        button_frame = tk.Frame(window_original_image)
        button_frame.pack(side=tk.BOTTOM, pady=10)

        # Create and pack buttons inside the frame
        add_view_button = tk.Button(button_frame, text="Add View", command=add_view)
        add_view_button.pack(side=tk.LEFT, padx=10)

        undo_button = tk.Button(button_frame, text="Undo Last View", command=undo_last_view)
        undo_button.pack(side=tk.LEFT, padx=10)

        # Change the button text to "Reset to Default" and link it to the updated function
        reset_button = tk.Button(button_frame, text="Reset to Default", command=reset_to_default)
        reset_button.pack(side=tk.LEFT, padx=10)

        crop_button = tk.Button(button_frame, text="Save Views", command=crop_views)
        crop_button.pack(side=tk.LEFT, padx=10)

        close_button = tk.Button(button_frame, text="Close Configuration", command=close_window)
        close_button.pack(side=tk.LEFT, padx=10)

        window_original_image.mainloop()

    else:
        messagebox.showinfo("Info", "No image has been loaded yet.")
        return



def main():
    root = tk.Tk()
    root.title("FLS Result Viewer (v2025.1.0a)")
    app = LogfileViewerApp(root)
    root.geometry('1360x930')
    root.minsize(1360,930) #prevention from resizing
    root.mainloop()

if __name__ == "__main__":
    main()
