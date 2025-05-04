from utils import get_logger
import os
import sys
import ctypes
from hilscher import CIFX70E_DP



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
application_path = get_application_path() 

print("Application path:", application_path)


def main():
    # Initialize global variables

    app_logger = get_logger()
    app_logger.info("Program started")
    app_logger.debug("Doing some debug-level work")
    app_logger.warning("Something non-fatal happened")


    return_code = 0
    szBoard = CIFX70E_DP.g_szBoard.value.decode('ascii')  # Board name
    szFirmwareFile = CIFX70E_DP.g_szFirmwareFile.value.decode('ascii')  # Firmware path
    szConfigFile = CIFX70E_DP.g_szConfigFile.value.decode('ascii')  # Config path
    ulTimerResolution = CIFX70E_DP.g_ulTimerResolution.value  # Timer resolution
    ulIOTimeout = CIFX70E_DP.g_ulIOTimeout.value  # I/O timeout
    # Initialize the driver handle
    CIFXHANDLE = ctypes.c_void_p
    hDriver = CIFXHANDLE(None)

    # Open the driver
    if CIFX70E_DP.wic_dll.xDriverOpen(ctypes.byref(hDriver)) != CIFX70E_DP.CIFX_NO_ERROR:
        print("Failed to open cifX70e driver.")
        app_logger.error("Failed to open cifX70e driver.")
        sys.exit(1)
    else:    
        print("cifX70e driver is open.")
        app_logger.info("cifX70e driver is open.")

    # Perform I/O operations

    #images_directory = "C:/Users/tgdev01/Desktop/pijus/cifXTest_Console2/pythonDetect/pythonDetect/2024-09-18/27.09.2024"  # Path
    #root_image = config.get(section='Settings', option='root_image', fallback='C:/Users/tgdev01/Documents/GitHub/fls/img')
    #print(root_image)

    #images_directory = "C:/Users/tgdev01/Documents/GitHub/fls/img"
    

    try:
        app_logger.info("\n--- Begin Operations ---")
       # print("\n--- Begin Operations ---")


        # 1. Read operation
        app_logger.info("\n--- Reading Data ---")
        CIFX70E_DP.WIC_ReadIOData(hDriver, szBoard, ulIOTimeout)
        #print("Image Context Data Read:", image_context.data_read) #TODO: Errror?

        # 2. Process operation
        app_logger.info("\n--- Processing Data ---")
        #error_context = ErrorContext(logfile="logfile.txt")

        """
        if success and result:
            print("Processing succeeded. Result:", result)
            pprint.pprint(image_context)
            image_context.increment_process()
        else:
            
            print("Processing failed. Check logfile.")
            sys.exit(1)

        # 3. Write operation
        print("\n--- Write Data ---")
        if success and result:
            CIFX70E_DP.WIC_SendToMaster(hDriver, szBoard, ulIOTimeout, result)
            image_context.increment_write()
            print("Write Operation Completed.")
            # Increment overall operation ID if all steps succeed
            image_context.increment_id()
        else:
            print("Write operation skipped due to processing failure.")
"""
    except Exception as e:
        print(f"An error occurred: {e}")
        return_code = 2

    finally:
        # Print counters
        
        #print("\n--- Operation Summary ---")
        #print(f"Total Read Operations: {image_context.read_count}")
        #print(f"Total Process Operations: {image_context.process_count}")
       # print(f"Total Write Operations: {image_context.write_count}")
        #print(f"Overall Operation ID: {image_context.id}")

        # Save counters to the file
        app_logger.info("Operation haved finished")

        # Close the driver
        if hDriver:
            CIFX70E_DP.wic_dll.xDriverClose(hDriver)
            print("cifX70e driver closed.")
            app_logger.info("cifX70e driver closed.")
        print(3)
    return return_code


if __name__ == "__main__":
    main()

"""
if __name__ == "__main__":
  try:
    # main fls function
    exit_code=main()
  except:
    print('Exit application.')
    #app_logger.exception('Exit application.')
    exit_code=4
    sys.exit(exit_code)
  print(exit_code)
  os._exit(exit_code)  # Exit with the return code from main
"""