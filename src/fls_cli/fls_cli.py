import time
from core import text_logger, image_processor
from core.config import get_config_path, get_cleaned_path
from core.system_validation import get_disk_status
import os
import sys
import ctypes
from profibus import CIFX70E_DP, Definitions, fls_simulator
import argparse
import configparser
import traceback

def get_application_path():
  '''
  Get path to the launched application by checking if running as a frozen exe or a standard script
  return: a joinable path string
  '''
  if getattr(sys, 'frozen', False):
    mypath = os.path.dirname(sys.executable)
  else:
    mypath = os.path.dirname(__file__)
  return mypath
##>


# get path of launched application
app_logger = text_logger.get_logger("FLS_CLI")
app_logger.info("Program started")

application_path = get_application_path() 
print("Application path:", application_path)



config = configparser.ConfigParser()
config_path = get_config_path()
config.read(config_path)
print("Config path", config_path)
Image_Config_Path = None

class ImageContext:
    def __init__(self):
        self.data_read = None
        self.data_write = None


CIFXHANDLE = ctypes.c_void_p
hDriver = CIFXHANDLE(None)


try:
    with open(config_path, 'r') as f:
        config.read_file(f)

    root_image_path = config.get("Settings", "root_image")
    Image_Config_Path  = root_image_path
except FileNotFoundError:
    print(f"Error: Config file '{config_path}' not found. Using default directories.")
except configparser.Error as e:
    print(f"Error reading config file: {e}. Using default directories.")


def run_all_tests(szBoard,ulIOTimeout):
    disk_health_checker()
    print("=== Starting Hardware Detection Tests ===\n")


    rc1 = CIFX70E_DP.test_no_driver(szBoard,ulIOTimeout)
    print("\n→ Waiting for next test...\n")
    time.sleep(2)

    rc2 = CIFX70E_DP.test_no_card(szBoard,ulIOTimeout)
    print("→ Waiting for next test...\n")
    time.sleep(2)

    rc3 = CIFX70E_DP.test_no_connection(szBoard,ulIOTimeout)
    print("→ Finalizing...\n")
    time.sleep(2)

    max_rc = max(rc1, rc2, rc3)

    if max_rc != 0:
        app_logger.error("")

        sys.exit(max_rc)


def disk_health_checker():

    #Check for disk usage and also print info about disk's

    disk_info_list = get_disk_status()

    for disk in disk_info_list:
        if disk["percent"] >= 95:
            app_logger.warning(
                f"CRITICAL DISK USAGE: {disk['device']} ({disk['mountpoint']}) is at {disk['percent']}% usage.")
    


def fls_run(szBoard, ulIOTimeout, hDriver, logger, simulate_only=False, image_path=None, simulated_input=None):
    """
    Main read-process-write loop for 'run' command.

    Parameters:
        hDriver (ctypes.c_void_p): The driver handle (None for simulator-only mode).
        logger (logging.Logger): Application logger.
        override_fields (dict): Field overrides from CLI (e.g. {'sp1': [100, 200]}).
        simulate_only (bool): If True, run in simulation-only mode.
    """

    logger.info("--- Starting run operation ---")

    image_context = ImageContext()

    # 1. Read (real or simulated)

    if image_path is None:
        logger.error("Image path is not provided.")
        print("Image path is missing. Use: run img=path/to/image.jpg")
        return
   

    """
        if override_fields:
            for key, val in override_fields.items():
                if hasattr(slave, key):
                    setattr(slave, key, val)
            fls_simulator.write_simulated_data(slave, application_path)
            logger.info("Simulator fields overridden and written.")
            """
    
    try:
        # 1. Read operation
        app_logger.info("\n--- Starting Reading Operation ---")
        #image_context.data_read = FLS_CIFX70E.WIC_ReadIOData(hDriver, szBoard, ulIOTimeout)
        #print("Image Context Data Read:", image_context.data_read) #TODO: Errror?

        if simulated_input is not None:
            logger.info("Using provided simulated input structure")
            image_context.data_read = simulated_input
        elif simulate_only or not hDriver:
            logger.info("No hardware information, starting to read from simulator")
            image_context.data_read = fls_simulator.simulate_input_structure(application_path)
        else:
            logger.info("Reading from hardware")
            image_context.data_read = CIFX70E_DP.FLS_ReadSingleIOData(hDriver, szBoard, ulIOTimeout)

        
        # 2. Process operation
        app_logger.info("\n--- Starting Processing Operation ---")

        success, result = image_processor.getResult(image_context, image_path)

        if success and result:
            app_logger.info(f"Processing succeeded. Result: {result}")
            print("Processing succeeded. Result:", result)
        else:
            print("Processing failed. Check logfile.")
            CIFX70E_DP.WIC_SendToMaster(hDriver, szBoard, ulIOTimeout, result)
            sys.exit(1)

        # 3. Write operation
        print("\n--- Starting Writing Operation ---")
        if success and result:
            CIFX70E_DP.WIC_SendToMaster(hDriver, szBoard, ulIOTimeout, result)
            app_logger.info("Writing back to composer operation completed.")
            print("Write Operation Completed.")

            # Increment overall operation ID if all steps succeed
        else:
            app_logger.warning("Write operation skipped due to processing failure.")
            print("Write operation skipped due to processing failure.")

    except Exception as e:
        app_logger.error(f"An error occurred Now: {e}")
        app_logger.exception("Detailed traceback:")
        print(f"An error occurred Now: {e}")
        traceback.print_exc() 
        return_code = 2

    finally:
        # Print counters
        
        #print("\n--- Operation Summary ---")
        #print(f"Total Read Operations: {image_context.read_count}")
        #print(f"Total Process Operations: {image_context.process_count}")
       # print(f"Total Write Operations: {image_context.write_count}")
        #print(f"Overall Operation ID: {image_context.id}")

        # Save counters to the file
        # Close the driver
        if hDriver:
            CIFX70E_DP.wic_dll.xDriverClose(hDriver)
            print("cifX70e driver closed.")
            app_logger.info("cifX70e driver closed.")

    app_logger.info("--- Run operation completed ---")

def get_fls_config():
    szBoard = CIFX70E_DP.g_szBoard.value.decode('ascii')
    szFirmwareFile = CIFX70E_DP.g_szFirmwareFile.value.decode('ascii')
    szConfigFile = CIFX70E_DP.g_szConfigFile.value.decode('ascii')
    ulTimerResolution = CIFX70E_DP.g_ulTimerResolution.value
    ulIOTimeout = CIFX70E_DP.g_ulIOTimeout.value

    return {
        "szBoard": szBoard,
        "szFirmwareFile": szFirmwareFile,
        "szConfigFile": szConfigFile,
        "ulTimerResolution": ulTimerResolution,
        "ulIOTimeout": ulIOTimeout
    }


def main():
    # Initialize global variables

    return_code = 0
    szBoard = CIFX70E_DP.g_szBoard.value.decode('ascii')  # Board name
    szFirmwareFile = CIFX70E_DP.g_szFirmwareFile.value.decode('ascii')  # Firmware path
    szConfigFile = CIFX70E_DP.g_szConfigFile.value.decode('ascii')  # Config path
    ulTimerResolution = CIFX70E_DP.g_ulTimerResolution.value  # Timer resolution
    ulIOTimeout = CIFX70E_DP.g_ulIOTimeout.value  # I/O timeout


    parser = argparse.ArgumentParser(description='Process operations with CIFX70E-DP card')
    parser.add_argument('-t', '--test', action='store_true', help='Process test operation')
    parser.add_argument('-d', '--watchdog', action='store_true', help='Process test watchdog termination')

    subparsers = parser.add_subparsers(dest='command')
    read_parser = subparsers.add_parser('read', help='Perform read operation N times or read specific fields')
    read_parser.add_argument('values', nargs='*',
                            help='Number of times to read (int) or field names to read (e.g. sp1 value_16)')

    write_parser = subparsers.add_parser('write', help='Process write operation')
    for name, ctype in Definitions.PbBufOutWic._fields_:
        if hasattr(ctype, "_length_") and hasattr(ctype, "_type_"):
            #array
            write_parser.add_argument(f'-{name}', action=CIFX70E_DP.PVKeyArrayAction, help=f'Comma-separated values for {name}, max 8')
        else:
            #single value
            write_parser.add_argument(f'-{name}', action=CIFX70E_DP.SingleValueAction, help=f'Integer value for {name}')

    run_parser = subparsers.add_parser('run', help='Run fls_run N times using Image_Config_Path')
    run_parser.add_argument('count', type=int, nargs='?', default=1, help='Number of times to run')


    args = parser.parse_args()

    data: Definitions.PbBufOutWicData = getattr(args, 'pb_data', Definitions.PbBufOutWicData())

    

# TODO: drop
    # setup_logging()
    # logging.basicConfig(level="INFO")
    # logger.debug("debug message", extra={"x": "hello"})
    # logger.info("info message")
    # logger.warning("warning message")
    # logger.error("error message")
    # logger.critical("critical message")
#
    run_all_tests(szBoard,ulIOTimeout)

    
    if CIFX70E_DP.wic_dll.xDriverOpen(ctypes.byref(hDriver)) != CIFX70E_DP.CIFX_NO_ERROR:
        print("Failed to open cifX70e driver,can only operate on simulation mode")
        app_logger.error("Failed to open cifX70e driver, can only operate on simulation mode")
        pass
        #sys.exit(1)
    else:    
        #print("cifX70e driver is open.")
        app_logger.info("cifX70e driver is open. Give an argument to process functions")
        

    if args.test:
       CIFX70E_DP.WIC_RunCifXConsoleTest(szBoard, szFirmwareFile, szConfigFile, ulTimerResolution, ulIOTimeout)

    elif args.command == 'read':
        simulation_only_fields = {field_name for field_name, _ in Definitions.PbBufInWic._fields_}
        simulate_mode = any('=' in val for val in args.values) or args.values and args.values[0] == 'sim'

        if not args.values:
            # Read once from hardware
            CIFX70E_DP.FLS_ReadIOData(hDriver, szBoard, ulIOTimeout, 1)

        elif simulate_mode:
            # Simulate structure
            slave = fls_simulator.simulate_input_structure(application_path)
            
            print("--- Simulated Field Injection ---")
            for item in args.values:
                if '=' in item:
                    field, val = item.split('=', 1)
                    if hasattr(slave, field):
                        current = getattr(slave, field)
                        try:
                            if isinstance(current, ctypes.Array):
                                values = [x.strip() for x in val.split(',')]
                                for i, x in enumerate(values):
                                    if x == '':
                                        continue  # skip empty value
                                    try:
                                        current[i] = int(x)
                                    except Exception as e:
                                        print(f"Error setting index {i} of {field}: {e}")
                            else:
                                setattr(slave, field, type(current)(val))
                            print(f"{field} = {val}")
                        except Exception as e:
                            print(f"Error setting {field}: {e}")
                    else:
                        print(f"Invalid field: {field}")
                else:
                    # Just print specific field
                    if hasattr(slave, item):
                        value = getattr(slave, item)
                        print(f"{item}: {list(value) if isinstance(value, ctypes.Array) else value}")
                    else:
                        print(f"Invalid field name: {item}")

            fls_simulator.write_simulated_data(slave, application_path)
            if not any('=' not in x for x in args.values):
                print("--- Simulated Full Read ---")
                for field_name, _ in Definitions.PbBufInWic._fields_:
                    value = getattr(slave, field_name)
                    print(f"{field_name}: {list(value) if isinstance(value, ctypes.Array) else value}")

        elif len(args.values) == 1 and args.values[0].isdigit():
            # Read N times from hardware
            CIFX70E_DP.FLS_ReadIOData(hDriver, szBoard, ulIOTimeout, int(args.values[0]))

        else:
            # Hardware read of specific fields
            slave = CIFX70E_DP.FLS_ReadSingleIOData(hDriver, szBoard, ulIOTimeout)
            if slave:
                for field_name in args.values:
                    if hasattr(slave, field_name):
                        value = getattr(slave, field_name)
                        print(f"{field_name}: {list(value) if isinstance(value, ctypes.Array) else value}")
                    else:
                        print(f"Invalid field name: {field_name}")
            else:
                print("Failed to read data.")
    elif args.command == 'write':
        data = getattr(args, 'pb_data', Definitions.PbBufOutWicData())
        buf = CIFX70E_DP.to_struct(data)
        CIFX70E_DP.print_PbBufOutWic(buf)
        print("Write mode enabled. Buffer populated.")
    elif args.watchdog:
       CIFX70E_DP.FLS_TestWatchdog(hDriver, szBoard)
    elif args.command == 'run':
        for i in range(args.count):
            print(f"\n--- Run {i + 1} of {args.count} ---")
            print("Image path", Image_Config_Path)
            fls_run(szBoard, ulIOTimeout, hDriver, app_logger, image_path=Image_Config_Path)
            time.sleep(10)  # sleep second between runs

    else:
        print(" Image path", Image_Config_Path )
        fls_run(szBoard, ulIOTimeout, hDriver, app_logger, image_path=Image_Config_Path)

   
    #CIFX70E_DP.WIC_RunCifXConsoleTest(szBoard, szFirmwareFile, szConfigFile, ulTimerResolution, ulIOTimeout)
    # Perform I/O operations

    #images_directory = "C:/Users/tgdev01/Desktop/pijus/cifXTest_Console2/pythonDetect/pythonDetect/2024-09-18/27.09.2024"  # Path
    #print(root_image)

    #images_directory = "C:/Users/tgdev01/Documents/GitHub/fls/img"
        # Print counters
        
        #print("\n--- Operation Summary ---")
        #print(f"Total Read Operations: {image_context.read_count}")
        #print(f"Total Process Operations: {image_context.process_count}")
       # print(f"Total Write Operations: {image_context.write_count}")
        #print(f"Overall Operation ID: {image_context.id}")

        # Save counters to the file
        app_logger.info("Operation haved finished")

        # Close the driver
   

if __name__ == "__main__":
  try:
    # main fls function
    exit_code=main()
  except:
    app_logger.info("Program closed")
    print('Exit application.')
    #app_logger.exception('Exit application.')
    exit_code=4
    sys.exit(exit_code)
  os._exit(exit_code)  # Exit with the return code from main
