import argparse
import ctypes
import time
from dataclasses import dataclass, field
from typing import List
import json
import os
import datetime
from .Definitions import PbBufInWic

STATE_FILE = "read_simulation.json"

@dataclass
class SimulatedData:
    state1: int = 0
    state2: int = 0
    year: int = 2025
    month: int = 5
    day: int = 16
    hours: int = 15
    minutes: int = 53
    seconds: int = 13
    interval1: int = 11
    interval2: int = 182
    interval3: int = 183
    interval4: int = 184
    value_13: int = 185
    value_14: int = 112
    value_15: int = 113
    value_16: int = 114
    sp1: List[int] = field(default_factory=lambda: [2000, 4000, 6000, 8000, 1501, 1601, 1701, 1801])
    sp2: List[int] = field(default_factory=lambda: [2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800])
    sp3: List[int] = field(default_factory=lambda: [3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800])
    sp4: List[int] = field(default_factory=lambda: [4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800])


@dataclass
class SimulatedDataWrite:
    state1: int = 0
    state2: int = 0
    year: int = 2025
    month: int = 5
    day: int = 16
    hours: int = 20
    minutes: int = 6
    seconds: int = 12
    interval1: int = 0
    interval2: int = 0
    interval3: int = 0
    interval4: int = 0
    value_13: int = 0
    value_14: int = 0
    value_15: int = 0
    value_16: int = 0
    pv1: List[int] = field(default_factory=lambda: [0] * 8)
    pvq1: List[int] = field(default_factory=lambda: [0] * 8)
    pv2: List[int] = field(default_factory=lambda: [0] * 8)
    pvq2: List[int] = field(default_factory=lambda: [0] * 8)
    pv3: List[int] = field(default_factory=lambda: [0] * 8)
    pvq3: List[int] = field(default_factory=lambda: [0] * 8)
    pv4: List[int] = field(default_factory=lambda: [0] * 8)
    pvq4: List[int] = field(default_factory=lambda: [0] * 8)


class TestContext:
    def __init__(self):
        self.data_read = None
        self.data_write = None


test_context = TestContext()


from ctypes import Array
from dataclasses import is_dataclass, fields

def dataclass_to_ctypes(dataclass_obj, ctypes_class):
    if not is_dataclass(dataclass_obj):
        raise TypeError("Expected a dataclass instance")

    ctypes_obj = ctypes_class()

    for field in fields(dataclass_obj):
        value = getattr(dataclass_obj, field.name)

        if hasattr(ctypes_class, '_fields_'):
            field_types = dict(ctypes_class._fields_)
            if field.name in field_types:
                target_type = field_types[field.name]

                # Handle array fields
                if isinstance(getattr(ctypes_obj, field.name), Array):
                    array_len = len(getattr(ctypes_obj, field.name))
                    setattr(ctypes_obj, field.name, target_type(*value[:array_len]))
                else:
                    setattr(ctypes_obj, field.name, value)
    return ctypes_obj


def ctypes_to_dataclass(ctypes_obj, dataclass_class):
    if not hasattr(ctypes_obj, "_fields_"):
        raise TypeError("Expected a ctypes.Structure instance")

    kwargs = {}

    for field_name, field_type in ctypes_obj._fields_:
        value = getattr(ctypes_obj, field_name)

        # Convert ctypes arrays to lists
        if isinstance(value, Array):
            value = list(value)

        kwargs[field_name] = value

    return dataclass_class(**kwargs)

""" Usage for convert data back and forth:
sim_data = SimulatedData()
pb_struct = dataclass_to_ctypes(sim_data, PbBufInWic)

# Later: convert back
sim_data_roundtrip = ctypes_to_dataclass(pb_struct, SimulatedData)
"""
def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(vars(data), f)

def load_state():
    if not os.path.exists(STATE_FILE):
        return SimulatedData()  # fallback default
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
    filtered_data = filter_data_for_class(data, SimulatedData)
    return SimulatedData(**filtered_data)

def simulate_read():
    """Simulate reading from hardware or last written state."""
    return load_state()

def run_read(times: int):
    count = 0
    last_data = None
    while times == 0 or count < times:
        data = simulate_read()
        last_data = data  # Save for return
        print(f"\n--- Read #{count + 1} ---")
        for field, value in vars(data).items():
            print(f"{field}: {value}")
        count += 1
        if times == 0:
            user_input = input("Press Enter to continue or 'q' to quit: ").strip().lower()
            if user_input == 'q':
                break
        else:
            time.sleep(3)
    return last_data 

def filter_data_for_class(data: dict, cls):
    """Filter a dictionary to only include fields defined in the given dataclass."""
    allowed_fields = {f.name for f in cls.__dataclass_fields__.values()}
    return {k: v for k, v in data.items() if k in allowed_fields}

def write_simulated_data(slave, application_path):
    data_dict = {}
    for field_name, _ in slave._fields_:
        val = getattr(slave, field_name)
        if isinstance(val, ctypes.Array):
            data_dict[field_name] = list(val)
        else:
            data_dict[field_name] = val

    sim_file = os.path.join(application_path, 'read_simulation.json')
    with open(sim_file, 'w') as f:
        json.dump(data_dict, f, indent=4)

def struct_to_dict(struct):
    result = {}
    for field_name, _ in struct._fields_:
        val = getattr(struct, field_name)
        result[field_name] = list(val) if isinstance(val, ctypes.Array) else val
    return result

def simulate_input_structure(application_path):
    filepath = os.path.join(application_path, "read_simulation.json")
    with open(filepath, 'r') as f:
        json_data = json.load(f)

    sim_data = PbBufInWic()

    for field, value in json_data.items():
        if hasattr(sim_data, field):
            current_attr = getattr(sim_data, field)
            if isinstance(current_attr, (list, tuple, ctypes.Array)) and isinstance(value, list):
                for i in range(min(len(current_attr), len(value))):
                    current_attr[i] = value[i]
            else:
                setattr(sim_data, field, value)
        else:
            print(f"Warning: Field '{field}' not in PbBufInWic")

    return sim_data

def simulate_write_data(args):
    now = datetime.datetime.now()
    data = SimulatedDataWrite(
        year=now.year,
        month=now.month,
        day=now.day,
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second
    )

    for key, val in vars(args).items():
        if val is not None:
            if key.startswith("pv") or key.startswith("pvq"):
                padded = [int(x) for x in val.split(",")] + [0] * 8
                setattr(data, key, padded[:8])
            else:
                setattr(data, key, val)

    print("\nWrite mode enabled. Buffer populated.")
    for field, value in vars(data).items():
        print(f"{field}: {value}")

    save_state(data)
    print("Image Context Data Read: None\ncifX70e driver closed.")
    return 3



def WIC_PrintPBStruct(pStruct):
    """
    Prints the contents of a pb_buf_in_wic structure.

    :param pStruct: An instance of PbBufInWic containing the data to print.
    """
    if pStruct is None:
        print("Invalid structure pointer.")
        return

    # Print date and time
    print("state1:", pStruct.state1)
    print("state2:", pStruct.state2)
    print("year:", pStruct.year)
    print("month:", pStruct.month)
    print("day:", pStruct.day)
    print("hours:", pStruct.hours)
    print("minutes:", pStruct.minutes)
    print("seconds:", pStruct.seconds)
    print("interval1:", pStruct.interval1)
    print("interval2:", pStruct.interval2)
    print("interval3:", pStruct.interval3)
    print("interval4:", pStruct.interval4)
    print("value_13:", pStruct.value_13)
    print("value_14:", pStruct.value_14)
    print("value_15:", pStruct.value_15)
    print("value_16:", pStruct.value_16)


    print("sp1:", list(pStruct.sp1))
    print("sp2:", list(pStruct.sp2))
    print("sp3:", list(pStruct.sp3))
    print("sp4:", list(pStruct.sp4))


def main():
    parser = argparse.ArgumentParser(description="Simulated Profibus CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # READ command
    read_parser = subparsers.add_parser("read", help="Read simulated data")
    read_parser.add_argument("times", type=int, help="Number of times to read (0 for infinite)")

    # WRITE command
    write_parser = subparsers.add_parser("write", help="Write simulated data")
    for i in range(1, 5):
        write_parser.add_argument(f"-pv{i}", type=str, help=f"Comma-separated list for pv{i}")
        write_parser.add_argument(f"-pvq{i}", type=str, help=f"Comma-separated list for pvq{i}")

    write_parser.add_argument("-state1", type=int, help="Set state1")
    write_parser.add_argument("-state2", type=int, help="Set state2")
    write_parser.add_argument("-interval1", type=int)
    write_parser.add_argument("-interval2", type=int)
    write_parser.add_argument("-interval3", type=int)
    write_parser.add_argument("-interval4", type=int)
    write_parser.add_argument("-value_13", type=int)
    write_parser.add_argument("-value_14", type=int)
    write_parser.add_argument("-value_15", type=int)
    write_parser.add_argument("-value_16", type=int)

    # READ command
    process_parser = subparsers.add_parser("process", help="Process simulated data")
    #process_parser.add_argument("times", type=int, help="Number of times to read (0 for infinite)")

    args = parser.parse_args()

    if args.command == "read":
        test_context.data_read=run_read(args.times)
    elif args.command == "write":
        test_context.data_write = simulate_write_data(args)
    elif args.command == "process":
        data = load_state()
        WIC_PrintPBStruct(data)


if __name__ == "__main__":
    main()

