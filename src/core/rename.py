import os
import re


class FileReader:
    def __init__(self, filepath):
        self.filepath = filepath
        self.headers = ['Timestamp', 'Tracks', 'Operator_setpoints', 'Processed_values',
                        'PV_quality', 'Image_name', 'View_name']
        self.entries = self._load_logfile()

    class LogEntry:
        def __init__(self, entry_dict):
            self.timestamp = entry_dict.get("Timestamp")
            self.tracks = int(entry_dict.get("Tracks"))
            self.operator_setpoints = self._parse_floats(entry_dict.get("Operator_setpoints"))
            self.processed_values = self._parse_floats(entry_dict.get("Processed_values"))
            self.pv_quality = self._parse_floats(entry_dict.get("PV_quality"))
            self.image_name = entry_dict.get("Image_name")
            self.view_name = entry_dict.get("View_name")

        def _parse_floats(self, text):
            return [float(x.strip()) for x in text.split(',') if x.strip().replace('.', '', 1).isdigit()]

        def print_info(self):
            print(f"Timestamp: {self.timestamp}")
            print(f"Number of Tracks: {self.tracks}")
            print(f"Operator Setpoints: {self.operator_setpoints}")
            print(f"Processed Values: {self.processed_values}")
            print(f"PV Quality: {self.pv_quality}")
            print(f"Image Name: {self.image_name}")
            print(f"View Name: {self.view_name}")
            print("-" * 40)
        
    def _load_logfile(self):
        entries = []
        if not self.filepath or not os.path.isfile(self.filepath):
            print(f"Logfile not found or invalid: {self.filepath}")
            return entries

        with open(self.filepath, 'r') as file:
            lines = file.readlines()
            for line in lines[1:]:  # skip
                if line.strip():
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) == len(self.headers):
                        entry_data = dict(zip(self.headers, parts))
                        entry = self.LogEntry(entry_data)
                        entries.append(entry)
        return entries

    def print_all_entries(self):
        if not self.entries:
            print("No entries found.")
        for i, entry in enumerate(self.entries, 1):
            print(f"\nLog Entry {i}")
            entry.print_info()



def append_letter_to_view_name_second(view_name: str) -> str:

    if not view_name or '.' not in view_name:
        return view_name

    name, ext = os.path.splitext(view_name)
    match = re.search(r"(#\d+)([a-z]?)$", name)
    if match:
        base = match.group(1)
        current_letter = match.group(2)
        if current_letter:
            next_letter = chr(ord(current_letter) + 1) if current_letter != 'z' else 'a'
        else:
            next_letter = 'a'
        new_name = f"{name[:-len(base + current_letter)]}{base}{next_letter}{ext}"
        return new_name
    else:
        return view_name
    

def get_unique_view_name(view_name: str, directory: str) -> str:
    candidate = view_name
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = append_letter_to_view_name_second(candidate)
    return candidate
