import ctypes
from ctypes import POINTER, c_char_p, c_int, c_ulong, c_char, c_uint16, Structure, create_string_buffer, ARRAY, Array


# Read definitions
TRACKS_PER_VIEW_MAX = 8

TIMECAPS = ctypes.Structure
CIFX_MAX_INFO_NAME_LENGTH = 16

# Define the DRIVER_INFORMATION structure
class DriverInformation(ctypes.Structure):
    _pack_ = 1  # Packed structure
    _fields_ = [
        ("abDriverVersion", ctypes.c_char * 32),  # Fixed-size array of 32 characters
        ("ulBoardCnt", ctypes.c_uint32),         # 32-bit unsigned integer
    ]


class SystemChannelSystemInfoBlock(ctypes.Structure):
    _pack_ = 1  # Ensure the structure is packed (like __CIFx_PACKED_PRE)
    _fields_ = [
        ("abCookie", ctypes.c_uint8 * 4),           # 0x00 "netX" cookie, array of 4 uint8_t
        ("ulDpmTotalSize", ctypes.c_uint32),        # 0x04 Total size of the dual-port memory in bytes
        ("ulDeviceNumber", ctypes.c_uint32),        # 0x08 Device number
        ("ulSerialNumber", ctypes.c_uint32),        # 0x0C Serial number
        ("ausHwOptions", ctypes.c_uint16 * 4),      # 0x10 Hardware options for ports 0..3
        ("usManufacturer", ctypes.c_uint16),        # 0x18 Manufacturer location
        ("usProductionDate", ctypes.c_uint16),      # 0x1A Production date
        ("ulLicenseFlags1", ctypes.c_uint32),       # 0x1C License code flags 1
        ("ulLicenseFlags2", ctypes.c_uint32),       # 0x20 License code flags 2
        ("usNetxLicenseID", ctypes.c_uint16),       # 0x24 netX license ID
        ("usNetxLicenseFlags", ctypes.c_uint16),    # 0x26 netX license flags
        ("usDeviceClass", ctypes.c_uint16),          # 0x28 netX device class
        ("bHwRevision", ctypes.c_uint8),             # 0x2A Hardware revision index
        ("bHwCompatibility", ctypes.c_uint8),        # 0x2B Hardware compatibility index
        ("bDevIdNumber", ctypes.c_uint8),            # 0x2C Device identification number (rotary switch)
        ("bReserved", ctypes.c_uint8),               # 0x2D Reserved byte
        ("usReserved", ctypes.c_uint16),             # 0x2E:0x2F Reserved
    ]

class BoardInformation(ctypes.Structure):
    _pack_ = 1  # Ensure packed structure
    _fields_ = [
        ("lBoardError", ctypes.c_int),                           # Global board error
        ("abBoardName", ctypes.c_char * CIFX_MAX_INFO_NAME_LENGTH),                      # Board name, with CIFx_MAX_INFO_NAME_LENTH
        ("abBoardAlias", ctypes.c_char * CIFX_MAX_INFO_NAME_LENGTH),                     # Board alias
        ("ulBoardID", ctypes.c_uint),                             # Unique board ID
        ("ulSystemError", ctypes.c_uint),                         # System error
        ("ulPhysicalAddress", ctypes.c_uint),                     # Physical address
        ("ulIrqNumber", ctypes.c_uint),                           # IRQ number
        ("bIrqEnabled", ctypes.c_ubyte),                          # IRQ enabled flag (uint8_t)
        ("ulChannelCnt", ctypes.c_uint),                          # Number of available channels
        ("ulDpmTotalSize", ctypes.c_uint),                        # Dual-Port memory size
        ("tSystemInfo", SystemChannelSystemInfoBlock),            # System information (from SYSTEM_CHANNEL_SYSTEM_INFO_BLOCK)
    ]

class ChannelInformation(ctypes.Structure):
    _pack_ = 1  # Packed structure to ensure proper alignment
    _fields_ = [
        ("abBoardName", ctypes.c_char * CIFX_MAX_INFO_NAME_LENGTH),  # Global board name
        ("abBoardAlias", ctypes.c_char * CIFX_MAX_INFO_NAME_LENGTH), # Global board alias name
        ("ulDeviceNumber", ctypes.c_uint32),                        # Global board device number
        ("ulSerialNumber", ctypes.c_uint32),                        # Global board serial number
        
        ("usFWMajor", ctypes.c_uint16),                             # Major Version of Channel Firmware
        ("usFWMinor", ctypes.c_uint16),                             # Minor Version of Channel Firmware
        ("usFWBuild", ctypes.c_uint16),                             # Build number of Channel Firmware
        ("usFWRevision", ctypes.c_uint16),                          # Revision of Channel Firmware
        ("bFWNameLength", ctypes.c_uint8),                          # Length of FW Name
        ("abFWName", ctypes.c_uint8 * 63),                          # Firmware Name
        ("usFWYear", ctypes.c_uint16),                              # Build Year of Firmware
        ("bFWMonth", ctypes.c_uint8),                               # Build Month of Firmware (1..12)
        ("bFWDay", ctypes.c_uint8),                                 # Build Day of Firmware (1..31)
        
        ("ulChannelError", ctypes.c_uint32),                        # Channel error
        ("ulOpenCnt", ctypes.c_uint32),                             # Channel open counter
        ("ulPutPacketCnt", ctypes.c_uint32),                        # Number of put packet commands
        ("ulGetPacketCnt", ctypes.c_uint32),                        # Number of get packet commands
        ("ulMailboxSize", ctypes.c_uint32),                         # Mailbox packet size in bytes
        ("ulIOInAreaCnt", ctypes.c_uint32),                         # Number of IO IN areas
        ("ulIOOutAreaCnt", ctypes.c_uint32),                        # Number of IO OUT areas
        ("ulHskSize", ctypes.c_uint32),                             # Size of the handshake cells
        ("ulNetxFlags", ctypes.c_uint32),                           # Actual netX state flags
        ("ulHostFlags", ctypes.c_uint32),                           # Actual Host flags
        ("ulHostCOSFlags", ctypes.c_uint32),                        # Actual Host COS flags
        ("ulDeviceCOSFlags", ctypes.c_uint32),                      # Actual Device COS flags
    ]


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
        # data load (max index range from [0..8])
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
        ("pv1", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq1", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pv2", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq2", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pv3", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq3", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pv4", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
        ("pvq4", ARRAY(c_uint16, TRACKS_PER_VIEW_MAX)),
    ]

slave_result = PbBufInWic()