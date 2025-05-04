import ctypes
from ctypes import POINTER, c_char_p, c_int, c_ulong, c_char, c_uint16, Structure, create_string_buffer, ARRAY, Array
import json
import msvcrt
import os
import sys
import time
from .Definitions import SystemChannelSystemInfoBlock, DriverInformation, BoardInformation, ChannelInformation, PbBufInWic, PbBufOutWic



# Load the DLL
wic_dll = ctypes.CDLL('C:/Windows/System32/cifX32dll.dll')
#C:/Windows/SysWOW64/cifX32dll.dll

"""
 ------------------------------------------------------------------------------------ */
/*  global definitions                                                                  */
/* ------------------------------------------------------------------------------------ */
"""
# typeef void* CIFXHANDLE;
MAX_PATH = 260  # Maximum path length, similar to the C definition of MAX_PATH

TIMERR_NOERROR = 0  # Placeholder, adjust as necessary
TIMECAPS = ctypes.Structure

winmm = ctypes.WinDLL('winmm.dll')

# Define the timer functions (timeGetDevCaps, timeBeginPeriod, timeEndPeriod)
timeGetDevCaps = winmm.timeGetDevCaps
timeBeginPeriod = winmm.timeBeginPeriod
timeEndPeriod = winmm.timeEndPeriod

# Define system time resolution handling
class TIMECAPS(ctypes.Structure):
    _fields_ = [
        ("wPeriodMin", ctypes.c_uint32),
        ("wPeriodMax", ctypes.c_uint32),
    ]

g_ulTimerResolution = ctypes.c_ulong(1)  # Default timer resolution = 1 ms
g_ulIOTimeout = ctypes.c_ulong(10)       # Default IO timeout = 10 ms

# Board name as a string of length 10
g_szBoard = create_string_buffer(10)  # Buffer for char array
g_szBoard.value = b"cifX0"  # Assign the string

# Firmware file path, equivalent to MAX_PATH length
g_szFirmwareFile = create_string_buffer(MAX_PATH)
g_szFirmwareFile.value = b"\\Windows\\cifxdpm.nxf"  # Assign the string

# Config file path, equivalent to MAX_PATH length
g_szConfigFile = create_string_buffer(MAX_PATH)
g_szConfigFile.value = b"\\Windows\\config.nxd"  # Assign the string

# definitions
CIFX_MAX_INFO_NAME_LENGTH = 16
CIFX_HOST_STATE_READY = 1
CIFX_BUS_STATE_ON = 1

# Read definitions
TRACKS_PER_VIEW_MAX = 8
SIZE_BUFFER_IN = 244 #we need to multiply by 2
SIZE_BUFFER_OUT = 244

# Define constants
CIFX_NO_ERROR = ctypes.c_int32(0x00000000).value
CIFX_NO_MORE_ENTRIES = ctypes.c_int32(0x800A0014).value

slave_result = PbBufInWic()

def fill_pb_buf_in_wic_data(data_read):
    """
    Populates the image context with metadata, setpoints, intervals, and timestamp extracted from data_read.

    Args:
        data_read (PbBufInWic): The data structure read from the device.

    Returns:
        dict: A dictionary containing the timestamp, intervals, and setpoints.
    """
    try:
        # Extract timestamp
        timestamp = {
            "year": data_read.year,
            "month": data_read.month,
            "day": data_read.day,
            "hours": data_read.hours,
            "minutes": data_read.minutes,
            "seconds": data_read.seconds,
        }

        # Extract intervals
        intervals = {
            "interval1": data_read.interval1,
            "interval2": data_read.interval2,
            "interval3": data_read.interval3,
            "interval4": data_read.interval4,
        }

        # Extract setpoints
        setpoints = {
            "sp1": list(data_read.sp1),
            "sp2": list(data_read.sp2),
            "sp3": list(data_read.sp3),
            "sp4": list(data_read.sp4),
        }

        # Combine all into a single dictionary
        populated_context = {
            "timestamp": timestamp,
            "intervals": intervals,
            "setpoints": setpoints,
        }

        return populated_context

    except AttributeError as e:
        print(f"Error while populating image context: {e}")
        raise

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise



def show_error(lError):
    if lError != CIFX_NO_ERROR:
        # Create a buffer to hold the error description
        szError = create_string_buffer(1024)  # Buffer size matches 1024 in the C code

        # Call the DLL function to retrieve the error description
        wic_dll.xDriverGetErrorDescription(
            lError, szError, ctypes.sizeof(szError)
        )

        # Print the error code and description
        error_description = szError.value.decode('ascii').rstrip(chr(0))
        print(f"Error: 0x{lError:X}, <{error_description}>")



def WIC_RunCifXConsoleTest( szBoard, szFirmwareFile, szConfigFile, ulTimerResolution, ulIOTimeout):
    # Open the driver
    driver_info = DriverInformation()
    CIFXHANDLE = ctypes.c_void_p
    hDriver = CIFXHANDLE(None)
    szBoardName = create_string_buffer(CIFX_MAX_INFO_NAME_LENGTH)

    if CIFX_NO_ERROR != wic_dll.xDriverOpen(ctypes.byref(hDriver)):
        print("Everything its not fine")
        return
    else:
        print("It's  fine")

    # Get driver information
    lRet = wic_dll.xDriverGetInformation(
        hDriver, ctypes.sizeof(driver_info), ctypes.byref(driver_info)
    )
    if lRet != CIFX_NO_ERROR:
        # Read and display the driver error description
        show_error(lRet)
    else:
        # Decode and print the driver version
        driver_version = driver_info.abDriverVersion.decode('ascii').rstrip(chr(0))
        print(f"Driver Version: {driver_version}\n")

    # Initialize variables for board enumeration
    fBoardFound = False  # Equivalent to bool
    ulBoardIdx = c_ulong(0)  # Unsigned long for board index
    ulBoardCount = c_ulong(0)  # Unsigned long for board count
    lBoardRet = CIFX_NO_ERROR  # Error code, initialized to CIFX_NO_ERROR
    
    while lBoardRet == CIFX_NO_ERROR:
        board_info = BoardInformation()  # Assuming a class representing board information
        lBoardRet = wic_dll.xDriverEnumBoards(hDriver, ulBoardIdx, ctypes.sizeof(board_info), ctypes.byref(board_info))

        if lBoardRet != CIFX_NO_ERROR:
            # No more boards
            break

        # Increment board counter
        ulBoardCount.value += 1

        # Board found
        ulChannelIdx = c_ulong(0)
        ulChannelCount = c_ulong(0)
        lChannelRet = CIFX_NO_ERROR

        print(f"Board{ulBoardIdx.value} Information:")
        print(f" Name : {board_info.abBoardName.decode('ascii').rstrip(chr(0))}")
        print(f" Alias: {board_info.abBoardAlias.decode('ascii').rstrip(chr(0))}")
        print(f" DevNr: {board_info.tSystemInfo.ulDeviceNumber}")
        print(f" SN   : {board_info.tSystemInfo.ulSerialNumber}")
        print("\n")

        # If no board name is passed, use first found
        if not szBoard or len(szBoard.strip()) == 0:
            print(f"No board name given, using first found board: {board_info.abBoardName.decode('ascii')}")
            szBoardName = board_info.abBoardName.decode('ascii')
            szBoard = szBoardName

        fBoardFound = True

        # Enumerate channels
        while lChannelRet == CIFX_NO_ERROR:
            # Read all channel information
            channel_info = ChannelInformation()  # Assuming a class representing channel information
            lChannelRet = wic_dll.xDriverEnumChannels(hDriver, ulBoardIdx, ulChannelIdx, ctypes.sizeof(channel_info), ctypes.byref(channel_info))

            if lChannelRet != CIFX_NO_ERROR:
                if lChannelRet != CIFX_NO_MORE_ENTRIES:
                    # Show information about the error
                    print(f"Error during xDriverEnumChannels(): Channel {ulChannelIdx.value}")
                    show_error(lChannelRet)
            else:
                # Increment channel counter
                ulChannelCount.value += 1

                # Print channel information
                print(f" Channel#{ulChannelIdx.value} Information:")
                print(f"   Channel Error            : 0x{channel_info.ulChannelError:08X}")
                print(f"   Board Name               : {bytes(channel_info.abBoardName).decode('ascii').rstrip(chr(0))}")
                print(f"   Alias Name               : {bytes(channel_info.abBoardAlias).decode('ascii').rstrip(chr(0))}")
                print(f"   Device Nr.               : {channel_info.ulDeviceNumber}")
                print(f"   Serial Nr.               : {channel_info.ulSerialNumber}")
                print(f"   MBX Size                 : {channel_info.ulMailboxSize}")
                print(f"   Firmware Name            : {bytes(channel_info.abFWName).decode('ascii').rstrip(chr(0))}")
                print(f"   Firmware Version         : {channel_info.usFWMajor}.{channel_info.usFWMinor}.{channel_info.usFWRevision} Build {channel_info.usFWBuild}")
                print(f"   Open Counter             : {channel_info.ulOpenCnt}")
                print(f"   Put Packet Counter       : {channel_info.ulPutPacketCnt}")
                print(f"   Get Packet Counter       : {channel_info.ulGetPacketCnt}")
                print(f"   Number of IO Input Areas : {channel_info.ulIOInAreaCnt}")
                print(f"   Number of IO Output Areas: {channel_info.ulIOOutAreaCnt}")
                print(f"   Size of handshake cells  : {channel_info.ulHskSize}")
                print(f"   Actual netX Flags        : 0x{channel_info.ulNetxFlags:08X}")
                print(f"   Actual host Flags        : 0x{channel_info.ulHostFlags:08X}")

            ulChannelIdx.value += 1  # Next channel

        print(f"Total channels on Board{ulBoardIdx.value}: {ulChannelCount.value}\n")
        ulBoardIdx.value += 1  # Next board

    print(f"Total number of boards found: {ulBoardCount.value}\n")
    print("\n************************************************")
    print(f"*** Running tests on device <{szBoard}>")
    print("************************************************\n")

    # If a board was found, proceed with I/O operations
    if fBoardFound:
        # Wait for user input to proceed with I/O data read/write
        print("\n*** Press (r) to READ I/O Data  (w) to WRITE I/O Data   (ESC) to QUIT ***")
        user_input = input().lower()

        if user_input == 'r':
            WIC_ReadIOData(hDriver, szBoard, ulIOTimeout)
            print("Performing reading operation")
        else:
            print("\n*** TERMINATING Communication to Profibus MASTER ... ***")


def WIC_ReadIOData(hDriver, szBoard, ulWaitTimeout):

    # Buffers to hold data
    lRet = CIFX_NO_ERROR
    abReadIOBuffer = (ctypes.c_byte * (SIZE_BUFFER_IN * 2))()
    #abLastValidIOBuffer = (ctypes.c_byte * (SIZE_BUFFER_IN *2))()

    # Initialize structures
    slave = PbBufInWic()
    #master = pb_buf_out()1
    # Open the channel

    szBoard_ctypes = ctypes.create_string_buffer(szBoard.encode('utf-8'))

    CIFXHANDLE = ctypes.c_void_p
    hDevice = CIFXHANDLE(None)

    lRet = wic_dll.xChannelOpen(ctypes.byref(hDriver), szBoard_ctypes, 0, ctypes.byref(hDevice))
    if lRet != CIFX_NO_ERROR:
        print("Error in xChannelOpen:")
        show_error(lRet)
        return
    else:
        print("Channel opened successfully.")

    # Ensure hDevice is valid
    if not hDevice:
        print("Invalid device handle.")
        return

    # Set device states
    ulState = ctypes.c_uint32(0)
    print("Setting host state to CIFX_HOST_STATE_READY...")
    lRet = wic_dll.xChannelHostState(hDevice, CIFX_HOST_STATE_READY, ctypes.byref(ulState), 1000)
    if lRet != CIFX_NO_ERROR:
        print(f"Error in xChannelHostState: {hex(lRet)}")
        show_error(lRet)
        wic_dll.xChannelClose(hDevice)
        return

    print("Setting bus state to CIFX_BUS_STATE_ON...")
    lRet = wic_dll.xChannelBusState(hDevice, CIFX_BUS_STATE_ON, ctypes.byref(ulState), 1000)
    if lRet != CIFX_NO_ERROR:
        print(f"Error in xChannelBusState: {hex(lRet)}")
        show_error(lRet)
        wic_dll.xChannelClose(hDevice)
        return

    print("\nContinuously reading I/O data from Profibus ...")
    bExitLoop = False

    while not bExitLoop:
        # Attempt to read data
        lRet = wic_dll.xChannelIORead(hDevice, 0, 0, SIZE_BUFFER_IN, ctypes.byref(abReadIOBuffer), ulWaitTimeout)
        if lRet != CIFX_NO_ERROR:
            print(f"ReadIOData(): READING data from IOBuffer failed. (Error: {lRet})")
            show_error(lRet)
            
        else:
            ctypes.memmove(ctypes.addressof(slave), abReadIOBuffer, ctypes.sizeof(slave))
            return slave
            
        # Check for keyboard input
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8').lower()
            if key in ('q', '\x1b'):  # 'q' or ESC
                print(f"\nKey '{key}' pressed. Exiting Profibus I/O loop ...")
                bExitLoop = True
            elif key == 'w':  # Write operation
                view = int(input("Enter view number (1-4): "))
                print(f"Writing data for view {view}")
                print("\n\nWRITING Copy of READ Buffer to MASTER ...")
                WIC_SendToMaster(hDriver, szBoard, ulWaitTimeout)
                print("\nDATA OUT: ")
                # Output data structure
                #print(master.data)

        print("\n\n*** Press (w) to WRITE I/O Data back to Profibus MASTER. (ESC) or (q) to quit ***")
        print("\n*********************************************************************************\n")

        # Delay for input
        time.sleep(3)  # Sleep for whatever seconds

    # Cleanup
    if hDevice != None:
        wic_dll.xChannelClose(hDevice)


def main():

    # Parse command-line arguments
    if len(sys.argv) == 1:
        print("CifX Test Program - Help")
        print("  Options: ")
        print("  -T: <Time resolution in milliseconds [1..n]>")
        print("  -W: <IO wait timeout in milliseconds [1..n]>")
        print("  -B: <cifX Board name cifX[1..n]>")
        print("  -F: <Path to firmware file>")
        print("  -C: <Path to config file>\n")

    # Display program settings
    print(f"Actual timer resolution = {g_ulTimerResolution.value} ms")
    print(f"Actual I/O wait timeout = {g_ulIOTimeout.value} ms\n")

    # Set the system clock to 1ms resolution
    tc = TIMECAPS()
    MMResult = timeGetDevCaps(ctypes.byref(tc), ctypes.sizeof(tc))
    if MMResult != TIMERR_NOERROR:
        print(f"FAILED to read actual SYSTEM-TIME-RESOLUTION, error: 0x{MMResult:X}")

    MMResult = timeBeginPeriod(g_ulTimerResolution.value)
    if MMResult != TIMERR_NOERROR:
        print(f"FAILED to change SYSTEM-TIME-RESOLUTION to 1 ms, error: 0x{MMResult:X}")

    # Run the CifX console test
    return_code = WIC_RunCifXConsoleTest(
        g_szBoard.value.decode('ascii'),
        g_szFirmwareFile.value.decode('ascii'),
        g_szConfigFile.value.decode('ascii'),
        g_ulTimerResolution.value,
        g_ulIOTimeout.value
    )

    # Reset the system clock to default resolution
    if MMResult == TIMERR_NOERROR:
        timeEndPeriod(g_ulTimerResolution.value)
        
    return return_code



def WIC_PrintPBStruct(pStruct):
    """
    Prints the contents of a pb_buf_in_wic structure.

    :param pStruct: An instance of PbBufInWic containing the data to print.
    """
    if pStruct is None:
        print("Invalid structure pointer.")
        return

    # Print date and time
    print(f"\nDate: {pStruct.year:04}-{pStruct.month:02}-{pStruct.day:02} "
          f"{pStruct.hours:02}:{pStruct.minutes:02}:{pStruct.seconds:02}")

    # Print intervals
    print("\nIntervals:")
    print(pStruct.interval1, pStruct.interval2, pStruct.interval3, pStruct.interval4)

    # Print unused values
    print("\nUnused values:")
    print(pStruct.value_13, pStruct.value_14, pStruct.value_15, pStruct.value_16)

    # Print setpoint values
    print("\nSetpoint (sp) values:")
    for i in range(len(pStruct.sp1)):
        print(f"sp1[{i}]: {pStruct.sp1[i]}")

    print("Setpoint2 (sp) values:")
    for i in range(len(pStruct.sp2)):
        print(f"sp2[{i}]: {pStruct.sp2[i]}")

    print("Setpoint3 (sp) values:")
    for i in range(len(pStruct.sp3)):
        print(f"sp3[{i}]: {pStruct.sp3[i]}")

    print("Setpoint4 (sp) values:")
    for i in range(len(pStruct.sp4)):
        print(f"sp4[{i}]: {pStruct.sp4[i]}")


def copy_struct(dest, src):
    """
    Copies all fields from the source struct to the destination struct.

    Args:
        dest: The destination struct.
        src: The source struct.
    """
    for field_name, _ in src._fields_:
        setattr(dest, field_name, getattr(src, field_name))


def print_PbBufOutWic(master):
    print("state1:", master.state1)
    print("state2:", master.state2)
    print("year:", master.year)
    print("month:", master.month)
    print("day:", master.day)
    print("hours:", master.hours)
    print("minutes:", master.minutes)
    print("seconds:", master.seconds)
    print("interval1:", master.interval1)
    print("interval2:", master.interval2)
    print("interval3:", master.interval3)
    print("interval4:", master.interval4)
    print("value_13:", master.value_13)
    print("value_14:", master.value_14)
    print("value_15:", master.value_15)
    print("value_16:", master.value_16)
    
    # Print each pv and pvq array
    print("pv1:", list(master.pv1))
    print("pvq1:", list(master.pvq1))
    print("pv2:", list(master.pv2))
    print("pvq2:", list(master.pvq2))
    print("pv3:", list(master.pv3))
    print("pvq3:", list(master.pvq3))
    print("pv4:", list(master.pv4))
    print("pvq4:", list(master.pvq4))

def WIC_SendToMaster(hDriver, szBoard, ulWaitTimeout, result):

    lRet = CIFX_NO_ERROR
    abWriteIOBuffer = (ctypes.c_byte * SIZE_BUFFER_OUT)() # Buffer to hold the data to write
    abReadIOBuffer = (ctypes.c_byte * SIZE_BUFFER_IN)()
    master = PbBufOutWic()
    # Implementation starts
    #master = PbBufOutWic()
    slave = PbBufInWic()
    print(hDriver, szBoard, ulWaitTimeout)
    copy_struct(master, result)
    print_PbBufOutWic(master)

    
    if ctypes.sizeof(master) > 244:
        raise ValueError(f"PbBufOutWic structure size ({ctypes.sizeof(PbBufOutWic)}) exceeds buffer size (244).")
    

    szBoard_ctypes = ctypes.create_string_buffer(szBoard.encode('utf-8'))
    CIFXHANDLE = ctypes.c_void_p
    hDevice = CIFXHANDLE(None)

    lRet = wic_dll.xChannelOpen(ctypes.byref(hDriver), szBoard_ctypes, 0, ctypes.byref(hDevice))
    if lRet != CIFX_NO_ERROR:
        print("Error in xChannelOpen:")
        show_error(lRet)
        return
    else:
        print("Channel opened successfully.")

    # Ensure hDevice is valid
    if not hDevice:
        print("Invalid device handle.")
        return

    # Set device states
    ulState = ctypes.c_uint32(0)
    print("Setting host state to CIFX_HOST_STATE_READY...")
    lRet = wic_dll.xChannelHostState(hDevice, CIFX_HOST_STATE_READY, ctypes.byref(ulState), 1000)
    if lRet != CIFX_NO_ERROR:
        print(f"Error in xChannelHostState: {hex(lRet)}")
        show_error(lRet)
        wic_dll.xChannelClose(hDevice)
        return

    print("Setting bus state to CIFX_BUS_STATE_ON...")
    lRet = wic_dll.xChannelBusState(hDevice, CIFX_BUS_STATE_ON, ctypes.byref(ulState), 1000)
    if lRet != CIFX_NO_ERROR:
        print(f"Error in xChannelBusState: {hex(lRet)}")
        show_error(lRet)
        wic_dll.xChannelClose(hDevice)
        return

    #Memcpy from master to a writing buffer
    
    
    # Write the buffer to the channel's I/O area

    #print_buffer(abWriteIOBuffer, ctypes.sizeof(PbBufOutWic))
    #WIC_print_buffer(result)

    ctypes.memmove(abWriteIOBuffer, ctypes.byref(master), ctypes.sizeof(master))
    
    #print("Buffer before memmove:", list(abWriteIOBuffer[:ctypes.sizeof(master)]))

    lRet = wic_dll.xChannelIOWrite(hDevice, 0, 0, SIZE_BUFFER_OUT, abWriteIOBuffer, ulWaitTimeout)
    if lRet != CIFX_NO_ERROR:
        print(f"SendToMaster: Sending data failed. (Error: {lRet})")
        show_error(lRet)
    else:
        print("\nSendToMaster: Data SENT successfully.\n")
        #ctypes.memmove(ctypes.addressof(master), abWriteIOBuffer, ctypes.sizeof(master))
        #WIC_PrintPBStruct(master)
        #WIC_print_buffer(abWriteIOBuffer, ctypes.sizeof(abWriteIOBuffer))

    # Optionally, read back the data to verify correct handling
    lRet = wic_dll.xChannelIORead(hDevice, 0, 0, SIZE_BUFFER_IN, abReadIOBuffer, ulWaitTimeout)
    if lRet != CIFX_NO_ERROR:
        print(f"SendToMaster: Reading data back from Master failed. (Error: {lRet})")
        show_error(lRet)
    else:
        print("READ Buffer back from Master:\n")
        ctypes.memmove(ctypes.addressof(slave), abReadIOBuffer, ctypes.sizeof(slave))
        WIC_PrintPBStruct(slave)

    # Close the channel
    if hDevice is not None:
        wic_dll.xChannelClose(hDevice)

if __name__ == "__main__":
    main()
"""
if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)  # Exit with the return code from main
"""