import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import logging
import logging.handlers
import os
import sys
import win32evtlogutil  
import win32evtlog      
import win32con         


#LOGGERSTYLE = 2

class SimpleGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Image Viewer")
        
        self.image_label = tk.Label(root)
        self.image_label.pack()
        
        self.open_button = tk.Button(root, text="Open Image", command=self.open_image)
        self.open_button.pack()
        
    def open_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not file_path:
            return
        
        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error", "Failed to open image.")
            return
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        photo = Image.fromarray(image_rgb)
        photo = ImageTk.PhotoImage(photo)
        
        self.image_label.config(image=photo)
        self.image_label.image = photo

def setup_logger(name="AppLogger", log_file="app.log", level=logging.DEBUG):
    """Configures and returns a logger based on LOGGERSTYLE."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Checking wheter handler is already used
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = None  # Default to None

    try:
        if LOGGERSTYLE == 1:  # Terminal 
            handler = logging.StreamHandler(sys.stdout)

        elif LOGGERSTYLE == 2:  # File
            handler = logging.FileHandler(log_file)

        elif LOGGERSTYLE == 3:  # Windows
            if os.name == "nt":
                event_source = "FLS_V1"
                
                # Register the event src
                try:
                    win32evtlogutil.ReportEvent(
                        event_source,
                        eventID=1,
                        eventCategory=0,
                        eventType=win32evtlog.EVENTLOG_INFORMATION_TYPE,
                        strings=["Initializing Windows Event Logger"],
                        data=b""
                    )
                except Exception as e:
                    print(f"Event Source Registration Failed: {e}")

                handler = logging.handlers.NTEventLogHandler(event_source)
            else:
                raise ValueError("Windows Event Log is only supported on Windows.")

        else:
            raise ValueError("Invalid LOGGERSTYLE. Choose 1 (Terminal), 2 (File), or 3 (Event).")

        if handler:
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    except Exception as e:
        print(f"Logger setup failed: {e}")

    return logger


def main():
    global app_logger
    app_logger = setup_logger()
    app_logger.info("Application has started.")
    app_logger.warning("This is a warning message.")
    app_logger.error("An error occurred!")
    root = tk.Tk()
    app = SimpleGUIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()