"""
FLS: Profibus DP Client Data Types to connect to the Master
"""

from ctypes import sizeof, Structure, c_uint16, ARRAY, Array
from datetime import datetime

# FLS types and constants

# maximum image views per captured image
VIEWS_MAX: int = 4

# maximum tracks per view
TRACKS_PER_VIEW_MAX: int = 8

# define a data type alias for 16-bit setpoint, process value or its quality value
# setpoint, process value or its quality
c_value16 = c_uint16 
 # array of setpoints or process values
c_value16_array = c_value16 * TRACKS_PER_VIEW_MAX

VALUE16_BYTES: int = sizeof(c_value16) # from ctypes
VALUE16_ARRAY_BYTES: int = VALUE16_BYTES * TRACKS_PER_VIEW_MAX

# size_int8 = sizeof(c_uint8)
# size_int16 = sizeof(c_uint16)
# CIFXHANDLE = cifx.CIFXHANDLE # device handle data type
# # device handle data type
# # CIFXHANDLE = c_void_p

class DataIn(Structure): # Profibus Client Receive Moduls (16 * uint16 + 64 * uint16)
    """ Digital twin of composer profibus In modules; send from master to client """
    _pack_ = 1
    _fields_ = [
        # Slot 1: Module Name '16 Words In'
        ("state1", c_uint16),       # max. 16 state bits set or throughput by master
        ("state2", c_uint16),       # max. 16 state bits set or throughput by master
        ("year", c_uint16),
        ("month", c_uint16),
        ("day", c_uint16),
        ("hours", c_uint16),
        ("minutes", c_uint16),
        ("seconds", c_uint16),
        # operator given intervals between two processed images (per view)
        ("interval1", c_uint16),
        ("interval2", c_uint16),
        ("interval3", c_uint16),
        ("interval4", c_uint16),
        # ("interval", c_uint16*VIEWS_MAX),
        # ("spare", c_uint16*VIEWS_MAX),
        # 4x spares [0..3]
        ("value_13", c_uint16),
        ("value_14", c_uint16),
        ("value_15", c_uint16),
        ("value_16", c_uint16),     # use as watchdog value by the Profibus Master ?
        # Slot 2: Module Name '64 Words In'
        # setpoints (max index range from [0..7])
        ("sp1", c_value16_array),
        ("sp2", c_value16_array),
        ("sp3", c_value16_array),
        ("sp4", c_value16_array),
    ]
    def __init__(self, state1: int = 0xEE, state2: int = 0xFF, **kwargs):
        """
        Initialize the DataOut structure with default values
        """
        super().__init__(**kwargs)
        self.state1 = state1
        self.state2 = state2
        self.year = 2000
        self.month = 6
        self.day = 18
        self.hours = 4
        self.minutes = 20
        self.seconds = 0
        self.interval1 = 21
        self.interval2 = 22
        self.interval3 = 23
        self.interval4 = 24
        self.value_13 = 13
        self.value_14 = 14
        self.value_15 = 15
        self.value_16 = 16

        self.sp1 = (1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008)
        self.sp2 = (2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008)
        self.sp3 = (3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008)
        self.sp4 = (4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008)
    
    @property
    def size(self) -> int:
        """
        Return the size of the DataIn structure
        """
        return sizeof(self)

    def __repr__(self) -> str:
        return (
            f"state1: 0x{self.state1:04X} (={self.state1:016b}),"
            f"\nstate2: 0x{self.state2:04X} (={self.state2:016b}),"
            f"\ntimestamp: {self.year:04}-{self.month:02}-{self.day:02}T{self.hours:02}:{self.minutes:02}:{self.seconds:02},"
            f"\ninterval1: {self.interval1}, interval2: {self.interval2}, interval3: {self.interval3}, interval4: {self.interval4}"
            f"\nvalue_13: {self.value_13}, value_14: {self.value_14}, value_15: {self.value_15}, value_16: {self.value_16}"
            f"\nsp1: {list(self.sp1)},"
            f"\nsp2: {list(self.sp2)},"
            f"\nsp3: {list(self.sp3)},"
            f"\nsp4: {list(self.sp4)}"
            # f""
        )
        # return f"{{ state1: {self.state1:-04X} ({self.state1:b}) state2: {self.state2:-04X}  year: {self.year:04} month: {self.month:02} day: {self.day:02} }}"
        # max. 16 state bits set or throughput by master

    def dict(self) -> dict:
        """
        Populates the image context with metadata, setpoints, intervals and
        timestamp extracted from data_reveived.

        Args:
            data_received (PbBufInWic): The data structure read from the device.

        Returns:
            dict: A dictionary containing the states, timestamp, intervals and setpoints.
            intervals and setpoints are set VIEWS_MAX times.
        """
        try:
            _states = {
                "state1": hex(self.state1),
                "state2": hex(self.state2),
            }

            # Extract timestamp
            _timestamp = {
                "year": self.year,
                "month": self.month,
                "day": self.day,
                "hours": self.hours,
                "minutes": self.minutes,
                "seconds": self.seconds,
            }

            # Extract intervals
            _intervals = {
                "interval1": self.interval1,
                "interval2": self.interval2,
                "interval3": self.interval3,
                "interval4": self.interval4,
            }

            _spares = {
                "value_13": self.value_13,
                "value_14": self.value_14,
                "value_15": self.value_15,
                "value_16": self.value_16,
            }

            # Extract setpoints
            # sp1 type: _ctypes.CField
            _setpoints = {
                "sp1": list(self.sp1),
                "sp2": list(self.sp2),
                "sp3": list(self.sp3),
                "sp4": list(self.sp4),
                # "sp4": list(self.sp4),
            }

            # Combine all into a single dictionary
            _result = {
                "states": _states,
                "timestamp": _timestamp,
                "intervals": _intervals,
                "spares": _spares,
                "setpoints": _setpoints,
            }
            return _result

        except AttributeError as e:
            print(f"Error while creating dictionary from received data: {e}")
            raise

        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

    def to_dict(self):
        now = datetime.now()
        result = {}
        for field_name, field_type in self._fields_:
            val = getattr(self, field_name)
            result[field_name] = list(val) if isinstance(val, Array) else val
        result['timestamp'] = now.isoformat()
        return result
    def __getitem__(self, key):
        return getattr(self, key)
    def __setitem__(self, key,value):
        setattr(self,key, value)

    def __iter__(self):
        return iter(self.dict())
    def reset(self):
        """Reset values to a initial state"""
        now = datetime.now()
        print(f'## {self.__class__.__name__}.reset @{now:%Y-%m-%d %H:%M:%S.%f}')

        # Slot 1: Module Name '16 Words In'
        self.state1 = 0
        self.state2 = 0
        self.year = int(now.year)
        self.month = int(now.month)
        self.day = int(now.day)
        self.hours = int(now.hour)
        self.minutes = int(now.minute)
        self.seconds = int(round(now.second,0))
        self.interval1 = 0
        self.interval2 = 0
        self.interval3 = 0
        self.interval4 = 0
        self.value_13 = 0
        self.value_14 = 0
        self.value_15 = 0
        self.value_16 = 0

        # Slot 2: Module Name '64 Words In'
        self.sp1 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.sp2 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.sp3 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.sp4 = (0, 0, 0, 0, 0, 0, 0, 0)

    def reset_test(self, state1: int = 0xEE, state2: int = 0xFF, **kwargs):
        """Reset to test values"""
        # Slot 1: Module Name '16 Words In'
        now = datetime.now()
        print(f'## {self.__class__.__name__}.reset_test @{now:%Y-%m-%d %H:%M:%S.%f}')

        self.state1 = int('0b0101010101010101', 2)    # base 2
        self.state2 = 0b1010101010101010
        self.year = int(now.year)
        self.month = int(now.month)
        self.day = int(now.day)
        self.hours = int(now.hour)
        self.minutes = int(now.minute)
        self.seconds = int(round(now.second,0))
        self.interval1 = 21
        self.interval2 = 22
        self.interval3 = 23
        self.interval4 = 24
        self.value_13 = 13
        self.value_14 = 14
        self.value_15 = 15
        self.value_16 = 16

        # Slot 2: Module Name '64 Words In'
        self.sp1 = (11, 12, 13, 14, 15, 16, 17, 18)
        self.sp2 = (21, 22, 23, 24, 25, 26, 27, 28)
        self.sp3 = (31, 32, 33, 34, 35, 36, 37, 38)
        self.sp4 = (41, 42, 43, 44, 45, 46, 47, 48)

# use byte strings (e.g., b"hello")
# Encode Unicode strings to bytes using .encode() if necessary.

class DataOut(Structure):
    """ module structure send from client to master """
    _pack_ = 1 # 1 ??
    _fields_ = [
        # Slot 1: Module Name '16 Words Out'
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
        # Slot 2: Module Name '64 Words Out'
        # process values + process values qualities
        ("pv1", c_value16_array), # alternative: ("pv1", c_values16),
        ("pv1q", c_value16_array),
        ("pv2", c_value16_array),
        ("pv2q", c_value16_array),
        ("pv3", c_value16_array),
        ("pv3q", c_value16_array),
        ("pv4", c_value16_array),
        ("pv4q", c_value16_array),

    ]

    def __init__(self, state1: int = 0xEE, state2: int = 0xFF, **kwargs):
        """
        Initialize the DataOut structure with default values
        """
        super().__init__(**kwargs)
        self.state1 = state1
        self.state2 = state2
        self.year = 2025
        self.month = 6
        self.day = 18
        self.hours = 4
        self.minutes = 20
        self.seconds = 0
        self.interval1 = 21
        self.interval2 = 22
        self.interval3 = 23
        self.interval4 = 24
        self.value_13 = 13
        self.value_14 = 14
        self.value_15 = 15
        self.value_16 = 16

        self.pv1 = (1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018)
        self.pv1q = (101, 102, 103, 104, 105, 106, 107, 108)
        self.pv2 = (2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028)
        self.pv2q = (201, 202, 203, 204, 205, 206, 207, 208)
        self.pv3 = (3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038)
        self.pv3q = (301, 302, 303, 304, 305, 306, 307, 308)
        self.pv4 = (4041, 4042, 4043, 4044, 4045, 4046, 4047, 4048)
        self.pv4q = (401, 402, 403, 404, 405, 406, 407, 408)
    
    @property
    def size(self) -> int:
        """
        Return the size of the DataOut structure
        """
        return sizeof(self)

    def __repr__(self) -> str:
        return (
            f"\nstate1: 0x{self.state1:04X} (=0b{self.state1:016b})"
            f"\nstate2: 0x{self.state2:04X} (=0b{self.state2:016b})"
            f"\ntimestamp: {self.year:04}-{self.month:02}-{self.day:02}T{self.hours:02}:{self.minutes:02}:{self.seconds:02}"
            f"\ninterval1: {self.interval1}, interval2: {self.interval2}, interval3: {self.interval3}, interval4: {self.interval4}"
            f"\nvalue_13: {self.value_13}, value_14: {self.value_14}, value_15: {self.value_15}, value_16: {self.value_16}"
            f"\npv1: {list(self.pv1)}, "
            f"pv1q: {list(self.pv1q)},"
            f"\npv2: {list(self.pv2)}, "
            f"pv2q: {list(self.pv2q)}, "
            f"\npv3: {list(self.pv3)}, "
            f"pv3q: {list(self.pv3q)}, "
            f"\npv4: {list(self.pv4)}, "
            f"pv4q: {list(self.pv4q)}"
        )

    def dict(self) -> dict:
        """
        Populates a dictionary with state, timestamp, interval, process & quality values.

        Args:
            data_out (PbBufInWic): The data structure send to the device.

        Returns:
            dict: A dictionary containing the state, timestamp, interval, process 
            and quality values for each view.
        """
        try:
            _states = {
                "state1": hex(self.state1),
                "state2": hex(self.state2),
            }

            # Extract timestamp
            _timestamp = {
                "year": self.year,
                "month": self.month,
                "day": self.day,
                "hours": self.hours,
                "minutes": self.minutes,
                "seconds": self.seconds,
            }

            # Extract intervals #TOTDO: create timer class
            _intervals = {
                "interval1": self.interval1,
                "interval2": self.interval2,
                "interval3": self.interval3,
                "interval4": self.interval4,
            }

            _spares = {
                "value_13": self.value_13,
                "value_14": self.value_14,
                "value_15": self.value_15,
                "value_16": self.value_16,
            }

            # Extract process values
            _values = {
                "pv1": list(self.pv1),
                "pv1q": list(self.pv1q),
                "pv2": list(self.pv2),
                "pv2q": list(self.pv2q),
                "pv3": list(self.pv3),
                "pv3q": list(self.pv3q),
                "pv4": list(self.pv4),
                "pv4q": list(self.pv4q),
            }

            # Combine all into a single dictionary
            _result = {
                "states": _states,
                "timestamp": _timestamp,
                "intervals": _intervals,
                "spares": _spares,
                "values": _values,
            }
            return _result

        except AttributeError as e:
            raise ValueError(f"Error while creating dictionary from sent data: {e}") from e

        except Exception as e:
            raise ValueError(f"Unexpected error: {e}") from e

    def reset(self):
        """Reset values to an initial state"""
        now = datetime.now()
        print(f'## {self.__class__.__name__}.reset @{now:%Y-%m-%d %H:%M:%S.%f}')

        # Slot 3: Module Name '16 Words Out'
        self.state1 = 0
        self.state2 = 0
        self.year = int(now.year)
        self.month = int(now.month)
        self.day = int(now.day)
        self.hours = int(now.hour)
        self.minutes = int(now.minute)
        self.seconds = int(round(now.second,0))
        self.interval1 = 0
        self.interval2 = 0
        self.interval3 = 0
        self.interval4 = 0
        self.value_13 = 0
        self.value_14 = 0
        self.value_15 = 0
        self.value_16 = 0

        # Slot 4: Module Name '64 Words Out'
        self.pv1 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv1q = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv2 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv2q = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv3 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv3q = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv4 = (0, 0, 0, 0, 0, 0, 0, 0)
        self.pv4q = (0, 0, 0, 0, 0, 0, 0, 0)

    def reset_test(self):
        """Reset to test values"""
        now = datetime.now()
        print(f'## {self.__class__.__name__}.reset_test @{now:%Y-%m-%d %H:%M:%S.%f}')

        # Slot 3: Module Name '16 Words Out'
        self.state1 = int('0b0101010101010101', 2)    # base 2
        self.state2 = 0b1010101010101010
        self.year = int(now.year)
        self.month = int(now.month)
        self.day = int(now.day)
        self.hours = int(now.hour)
        self.minutes = int(now.minute)
        self.seconds = int(round(now.second,0))
        self.interval1 = 21
        self.interval2 = 22
        self.interval3 = 23
        self.interval4 = 24
        self.value_13 = 13
        self.value_14 = 14
        self.value_15 = 15
        self.value_16 = 16

        # Slot 4: Module Name '64 Words Out'
        self.pv1 = (1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018)
        self.pv1q = (101, 102, 103, 104, 105, 106, 107, 108)
        self.pv2 = (2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028)
        self.pv2q = (201, 202, 203, 204, 205, 206, 207, 208)
        self.pv3 = (3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038)
        self.pv3q = (301, 302, 303, 304, 305, 306, 307, 308)
        self.pv4 = (4041, 4042, 4043, 4044, 4045, 4046, 4047, 4048)
        self.pv4q = (401, 402, 403, 404, 405, 406, 407, 408)

DATA_IN_BYTES: int = sizeof(DataIn) # from ctypes
DATA_OUT_BYTES: int = sizeof(DataOut) # from ctypes