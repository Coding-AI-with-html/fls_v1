import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2

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

def main():
    root = tk.Tk()
    app = SimpleGUIApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()