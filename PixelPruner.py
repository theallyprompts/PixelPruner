import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
import os
import subprocess
import zipfile
from datetime import datetime
import webbrowser

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class PixelPruner:
    def __init__(self, master):
        self.master = master
        self.master.title("PixelPruner")

        control_frame = tk.Frame(master)
        control_frame.pack(fill=tk.X, side=tk.TOP)

        tk.Label(control_frame, text="Select crop size:").pack(side=tk.LEFT, padx=(10, 2))
        
        self.size_var = tk.StringVar()
        self.size_dropdown = ttk.Combobox(control_frame, textvariable=self.size_var, state="readonly", values=["512x512", "768x768", "1024x1024", "2048x2048"])
        self.size_dropdown.pack(side=tk.LEFT, padx=(2, 20))
        self.size_dropdown.set("512x512")  # Default size
        self.size_dropdown.bind("<<ComboboxSelected>>", self.update_crop_box_size)
        ToolTip(self.size_dropdown, "Choose the size of the crop area")

        self.prev_button = tk.Button(control_frame, text="< Prev", command=self.load_previous_image)
        self.prev_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.prev_button, "Load the previous image")

        self.next_button = tk.Button(control_frame, text="Next >", command=self.load_next_image)
        self.next_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.next_button, "Load the next image")

        try:
            self.rotate_left_image = tk.PhotoImage(file="rotate_left.png")
        except Exception as e:
            print(f"Error loading rotate_left.png: {e}")
            self.rotate_left_image = tk.PhotoImage()  # Placeholder if load fails

        # Load rotate right image
        try:
            self.rotate_right_image = tk.PhotoImage(file="rotate_right.png")
        except Exception as e:
            print(f"Error loading rotate_right.png: {e}")
            self.rotate_right_image = tk.PhotoImage()  # Placeholder if load fails

        self.rotate_left_button = tk.Button(control_frame, image=self.rotate_left_image, command=lambda: self.rotate_image(90))
        self.rotate_left_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.rotate_left_button, "Rotate image counterclockwise")

        self.rotate_right_button = tk.Button(control_frame, image=self.rotate_right_image, command=lambda: self.rotate_image(-90))
        self.rotate_right_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.rotate_right_button, "Rotate image clockwise")


        self.output_folder_button = tk.Button(control_frame, text="Set Output Folder", command=self.select_output_folder)
        self.output_folder_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.output_folder_button, "Select a folder to save cropped images")

        self.open_folder_icon = tk.PhotoImage(file="folder.png")
        self.open_folder_button = tk.Button(control_frame, image=self.open_folder_icon, command=self.open_output_folder)
        self.open_folder_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.open_folder_button, "Open the custom output folder")

        self.zip_button = tk.Button(control_frame, text="Zip Crops (0)", command=self.zip_crops)
        self.zip_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.zip_button, "Zip all cropped images")

        self.preview_toggle_button = tk.Button(control_frame, text="Preview", command=lambda: self.toggle_pane("preview"))
        self.preview_toggle_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.preview_toggle_button, "Toggle the preview pane")

        self.crops_toggle_button = tk.Button(control_frame, text="Show Crops", command=lambda: self.toggle_pane("crops"))
        self.crops_toggle_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.crops_toggle_button, "Toggle the crop thumbnails pane")

        self.undo_button = tk.Button(control_frame, text="Undo Last Crop", command=self.undo_last_crop)
        self.undo_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.undo_button, "Undo the last crop")

        self.about_button = tk.Button(control_frame, text="About", command=self.show_about)
        self.about_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.about_button, "About this application")

        self.exit_button = tk.Button(control_frame, text="Exit App", command=self.master.quit)
        self.exit_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.exit_button, "Exit the application")

        self.image_counter_label = tk.Label(control_frame, text="0/0")
        self.image_counter_label.pack(side=tk.RIGHT, padx=(10, 20))

        self.canvas = tk.Canvas(master, cursor="cross", bg="gray")
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        self.preview_canvas = tk.Canvas(master, width=512, height=512, bg="gray")
        self.preview_canvas.pack_forget()  # Hide preview pane initially

        # Create a frame for the crops pane with a scrollable canvas
        self.crops_frame = tk.Frame(master)
        self.crops_canvas = tk.Canvas(self.crops_frame, bg="gray", width=266)  # Set width to fit 2 thumbnails and spacing
        self.crops_scrollbar = tk.Scrollbar(self.crops_frame, orient="vertical", command=self.crops_canvas.yview)
        self.crops_canvas.configure(yscrollcommand=self.crops_scrollbar.set)
        self.crops_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.crops_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.crops_frame.pack_forget()  # Hide crops pane initially

        self.folder_path = filedialog.askdirectory(title="Select Folder with Images")
        if not self.folder_path or not os.listdir(self.folder_path):
            messagebox.showerror("Error", "No images found in the selected directory.")
            self.master.destroy()
            return
        self.images = [os.path.join(self.folder_path, img) for img in os.listdir(self.folder_path) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not self.images:
            messagebox.showerror("Error", "No valid images found in the selected directory.")
            self.master.destroy()
            return
        self.image_index = 0
        self.current_image = None
        self.image_scale = 1
        self.rect = None
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.output_folder = self.folder_path
        self.original_size = (512, 512)
        self.current_size = (512, 512)
        self.crop_counter = 0  # Global counter for all crops
        self.cropped_images = []  # List to keep track of cropped images
        self.cropped_thumbnails = []  # List to keep track of cropped thumbnails
        self.preview_enabled = False  # Preview pane toggle
        self.crops_enabled = False  # Crop thumbnails pane toggle
        self.update_image_counter()

        # Update the window and canvas sizes before displaying the first image
        self.master.update_idletasks()
        self.canvas.update_idletasks()

        self.load_image()

        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.master.minsize(1300, 750)  # Set a minimum size for the window

        # Bind keyboard shortcuts
        self.master.bind("w", lambda event: self.load_next_image())
        self.master.bind("s", lambda event: self.load_previous_image())
        self.master.bind("a", lambda event: self.rotate_image(90))
        self.master.bind("d", lambda event: self.rotate_image(-90))
        
        # Set the focus to the master window
        master.focus_set()
        
        # Center the window on the screen
        self.center_window()

        # Open the dropdown menu to ensure a size is selected
        self.size_dropdown.event_generate('<Button-1>')

        # Workaround to ensure the first image is centered
        self.master.after(100, self.load_next_image)
        self.master.after(200, self.load_previous_image)

        # Enable mouse wheel scrolling for the crops canvas
        self.crops_canvas.bind("<Enter>", self.bind_crops_mouse_wheel)
        self.crops_canvas.bind("<Leave>", self.unbind_crops_mouse_wheel)

    def center_window(self):
        self.master.update_idletasks()
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.master.geometry(f'{window_width}x{window_height}+{x}+{y}')

    def update_image_counter(self):
        self.image_counter_label.config(text=f"{self.image_index + 1}/{len(self.images)}")

    def update_zip_button(self):
        self.zip_button.config(text=f"Zip Crops ({len(self.cropped_images)})")

    def load_image(self):
        if 0 <= self.image_index < len(self.images):
            try:
                image_path = self.images[self.image_index]
                self.current_image = Image.open(image_path)
            except IOError:
                messagebox.showerror("Error", f"Failed to load image: {image_path}")
                return

            self.display_image()

    def display_image(self):
        aspect_ratio = self.current_image.width / self.current_image.height
        self.scaled_width = min(800, self.current_image.width)
        self.scaled_height = int(self.scaled_width / aspect_ratio) if aspect_ratio > 1 else min(600, self.current_image.height)
        self.scaled_width = int(self.scaled_height * aspect_ratio) if self.scaled_height < self.scaled_width else self.scaled_width
        self.tkimage = ImageTk.PhotoImage(self.current_image.resize((self.scaled_width, self.scaled_height), Image.ANTIALIAS))
        
        # Center the image within the canvas
        self.center_image_on_canvas()

        self.canvas.delete("all")
        self.canvas.create_image(self.image_offset_x, self.image_offset_y, anchor="nw", image=self.tkimage)
        self.image_scale = self.current_image.width / self.scaled_width
        size = tuple(map(int, self.size_var.get().split('x')))
        self.original_size = size
        self.current_size = size
        scaled_size = (int(size[0] / self.image_scale), int(size[1] / self.image_scale))  # Define scaled_size here
        self.rect = self.canvas.create_rectangle(self.image_offset_x, self.image_offset_y, self.image_offset_x + scaled_size[0], self.image_offset_y + scaled_size[1], outline='red')
        self.update_crop_box_size()
        self.update_image_counter()

    def center_image_on_canvas(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.image_offset_x = (canvas_width - self.scaled_width) // 2
        self.image_offset_y = (canvas_height - self.scaled_height) // 2

    def rotate_image(self, angle):
        if self.current_image:
            self.current_image = self.current_image.rotate(angle, expand=True)
            self.display_image()

    def update_crop_box_size(self, event=None):
        if self.rect:
            self.canvas.delete(self.rect)  # Remove existing rectangle before creating a new one
            size = tuple(map(int, self.size_var.get().split('x')))
            self.original_size = size
            self.current_size = size
            scaled_size = (int(size[0] / self.image_scale), int(size[1] / self.image_scale))
            if scaled_size[0] > self.scaled_width:
                scaled_size = (self.scaled_width, self.scaled_width)
            if scaled_size[1] > self.scaled_height:
                scaled_size = (self.scaled_height, self.scaled_height)
            self.rect = self.canvas.create_rectangle(self.image_offset_x, self.image_offset_y, self.image_offset_x + scaled_size[0], self.image_offset_y + scaled_size[1], outline='red')

    def on_mouse_move(self, event):
        if self.rect:
            size = self.current_size
            scaled_size = (int(size[0] / self.image_scale), int(size[1] / self.image_scale))
            if scaled_size[0] > self.scaled_width:
                scaled_size = (self.scaled_width, self.scaled_width)
            if scaled_size[1] > self.scaled_height:
                scaled_size = (self.scaled_height, self.scaled_height)
            x1, y1 = max(self.image_offset_x, min(event.x, self.image_offset_x + self.scaled_width - scaled_size[0])), max(self.image_offset_y, min(event.y, self.image_offset_y + self.scaled_height - scaled_size[1]))
            x2, y2 = x1 + scaled_size[0], y1 + scaled_size[1]
            self.canvas.coords(self.rect, x1, y1, x2, y2)
            
            if self.preview_enabled:
                self.update_preview(x1, y1, x2, y2)

    def update_preview(self, x1, y1, x2, y2):
        if self.current_image:
            real_x1, real_y1 = (x1 - self.image_offset_x) * self.image_scale, (y1 - self.image_offset_y) * self.image_scale
            real_x2, real_y2 = (x2 - self.image_offset_x) * self.image_scale, (y2 - self.image_offset_y) * self.image_scale
            if real_x1 > real_x2:
                real_x1, real_x2 = real_x2, real_x1
            if real_y1 > real_y2:
                real_y1, real_y2 = real_y2, real_y1
            cropped = self.current_image.crop((real_x1, real_y1, real_x2, real_y2))
            cropped = cropped.resize((512, 512))  # Larger fixed size preview
            self.tkpreview = ImageTk.PhotoImage(cropped)
            self.preview_canvas.delete("all")
            preview_canvas_width = self.preview_canvas.winfo_width()
            preview_canvas_height = self.preview_canvas.winfo_height()
            preview_offset_x = (preview_canvas_width - 512) // 2
            preview_offset_y = (preview_canvas_height - 512) // 2
            self.preview_canvas.create_image(preview_offset_x, preview_offset_y, anchor="nw", image=self.tkpreview)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_button_release(self, event):
        self.perform_crop()

    def on_mouse_wheel(self, event):
        if self.rect:
            increment = 50 if event.delta > 0 else -50
            new_width = self.current_size[0] + increment
            new_height = self.current_size[1] + increment
            if new_width < 50 or new_height < 50:
                return  # Prevent the rectangle from becoming too small
            scaled_width = int(new_width / self.image_scale)
            scaled_height = int(new_height / self.image_scale)
            if scaled_width > self.scaled_width or scaled_height > self.scaled_height:
                return  # Prevent the rectangle from extending beyond the image boundaries
            x1, y1, x2, y2 = self.canvas.coords(self.rect)
            new_x2 = x1 + scaled_width
            new_y2 = y1 + scaled_height
            self.canvas.coords(self.rect, x1, y1, new_x2, new_y2)
            self.current_size = (new_width, new_height)

    def bind_crops_mouse_wheel(self, event):
        self.crops_canvas.bind_all("<MouseWheel>", self.on_crops_mouse_wheel)

    def unbind_crops_mouse_wheel(self, event):
        self.crops_canvas.unbind_all("<MouseWheel>")

    def on_crops_mouse_wheel(self, event):
        self.crops_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def crop_image(self, x1, y1, x2, y2):
        real_x1, real_y1 = (x1 - self.image_offset_x) * self.image_scale, (y1 - self.image_offset_y) * self.image_scale
        real_x2, real_y2 = (x2 - self.image_offset_x) * self.image_scale, (y2 - self.image_offset_y) * self.image_scale
        if real_x1 > real_x2:
            real_x1, real_x2 = real_x2, real_x1
        if real_y1 > real_y2:
            real_y1, real_y2 = real_y2, real_y1
        size = self.current_size
        cropped = self.current_image.crop((real_x1, real_y1, real_x2, real_y2))
        cropped = cropped.resize(self.original_size)

        # Generate a unique filename by appending a global counter
        self.crop_counter += 1
        image_path = self.images[self.image_index]
        base_filename = os.path.basename(image_path)
        filename, ext = os.path.splitext(base_filename)
        cropped_filename = f"cropped_{self.crop_counter}_{filename}.png"
        cropped_filepath = os.path.join(self.output_folder, cropped_filename)
        cropped.save(cropped_filepath, "PNG")
        self.cropped_images.insert(0, cropped_filepath)  # Insert at the beginning of the list
        self.update_zip_button()

        # Create thumbnail and update crops canvas
        self.update_crops_canvas(cropped, cropped_filepath)

    def update_crops_canvas(self, cropped, filepath):
        cropped.thumbnail((128, 128))  # Create smaller thumbnail
        tkthumbnail = ImageTk.PhotoImage(cropped)
        self.cropped_thumbnails.insert(0, (tkthumbnail, filepath))  # Insert at the beginning of the list

        self.crops_canvas.delete("all")  # Clear previous thumbnails
        cols = 2  # Number of columns in the grid
        spacing = 10  # Space between thumbnails

        for index, (thumbnail, path) in enumerate(self.cropped_thumbnails):
            row, col = divmod(index, cols)
            x, y = col * (128 + spacing), row * (128 + spacing)
            self.crops_canvas.create_image(x, y, anchor="nw", image=thumbnail)

        # Update scroll region to accommodate all thumbnails
        self.crops_canvas.config(scrollregion=self.crops_canvas.bbox("all"))

    def perform_crop(self):
        x1, y1, x2, y2 = self.canvas.coords(self.rect)
        self.crop_image(x1, y1, x2, y2)
        self.load_next_image()

    def load_next_image(self):
        self.image_index = (self.image_index + 1) % len(self.images)
        self.load_image()

    def load_previous_image(self):
        self.image_index = (self.image_index - 1) % len(self.images)
        self.load_image()

    def select_output_folder(self):
        selected_folder = filedialog.askdirectory(title="Select Custom Output Folder")
        if selected_folder:
            self.output_folder = selected_folder
        else:
            messagebox.showwarning("Warning", "No output folder selected. Using the current folder.")

    def open_output_folder(self):
        if os.path.isdir(self.output_folder):
            subprocess.Popen(f'explorer {os.path.realpath(self.output_folder)}')

    def zip_crops(self):
        if not self.cropped_images:
            messagebox.showinfo("Info", "No cropped images to zip.")
            return

        num_images = len(self.cropped_images)
        current_date = datetime.now().strftime("%Y%m%d")
        zip_filename = os.path.join(self.output_folder, f"{num_images}_{current_date}.zip")

        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in self.cropped_images:
                zipf.write(file, os.path.basename(file))

        messagebox.showinfo("Info", f"Cropped images have been zipped into {zip_filename}")

    def toggle_pane(self, pane):
        if pane == "preview":
            self.preview_enabled = not self.preview_enabled
            self.crops_enabled = False
        elif pane == "crops":
            self.crops_enabled = not self.crops_enabled
            self.preview_enabled = False

        if self.preview_enabled:
            self.master.geometry(f"1550x800")  # Adjusted size to fit the larger preview pane
            self.preview_canvas.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=False)
            self.crops_frame.pack_forget()
        elif self.crops_enabled:
            self.master.geometry(f"1350x770")  # Adjusted size to fit the crops pane
            self.crops_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=False)
            self.preview_canvas.pack_forget()
        else:
            self.preview_canvas.pack_forget()
            self.crops_frame.pack_forget()
            self.master.geometry(f"1300x750")  # Resize the window back to normal
        
        # Workaround to ensure the main image is centered after toggling panes
        self.master.after(100, self.load_next_image)
        self.master.after(200, self.load_previous_image)

    def undo_last_crop(self):
        if not self.cropped_images:
            messagebox.showinfo("Info", "No cropped images to undo.")
            return

        last_cropped_image = self.cropped_images.pop(0)  # Remove the first item in the list
        if os.path.exists(last_cropped_image):
            os.remove(last_cropped_image)

        self.cropped_thumbnails.pop(0)
        self.update_crops_canvas_layout()
        self.update_zip_button()
        messagebox.showinfo("Info", "Last crop has been undone.")

    def update_crops_canvas_layout(self):
        self.crops_canvas.delete("all")  # Clear previous thumbnails
        cols = 2  # Number of columns in the grid
        spacing = 10  # Space between thumbnails

        for index, (thumbnail, path) in enumerate(self.cropped_thumbnails):
            row, col = divmod(index, cols)
            x, y = col * (128 + spacing), row * (128 + spacing)
            self.crops_canvas.create_image(x, y, anchor="nw", image=thumbnail)

        # Update scroll region to accommodate all thumbnails
        self.crops_canvas.config(scrollregion=self.crops_canvas.bbox("all"))

    def show_about(self):
        about_window = tk.Toplevel(self.master)
        about_window.title("About")
        about_window.geometry("400x200")
        about_window.resizable(False, False)

        # Center the about window
        about_window.update_idletasks()
        window_width = about_window.winfo_width()
        window_height = about_window.winfo_height()
        screen_width = about_window.winfo_screenwidth()
        screen_height = about_window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        about_window.geometry(f'{window_width}x{window_height}+{x}+{y}')

        about_text = (
            "Made by: TheAlly\n\n"
            "About: Prepare your LoRA training data with ease! "
            "Check out the GitHub Repo for the full feature list.\n\n"
        )
        
        label = tk.Label(about_window, text=about_text, justify=tk.LEFT, padx=10, pady=10, wraplength=380)
        label.pack(fill="both", expand=True)

        link_frame = tk.Frame(about_window)
        link_frame.pack(fill="both", expand=True)

        profile_label = tk.Label(link_frame, text="GitHub Repository:", justify=tk.LEFT, padx=10)
        profile_label.pack(side=tk.LEFT)
        link = tk.Label(link_frame, text="https://github.com/theallyprompts/PixelPruner", fg="blue", cursor="hand2", padx=10)
        link.pack(side=tk.LEFT)
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/theallyprompts/PixelPruner"))

        close_button = tk.Button(about_window, text="Close", command=about_window.destroy)
        close_button.pack(pady=10)

def main():
    root = tk.Tk()
    app = PixelPruner(root)
    root.mainloop()

if __name__ == "__main__":
    main()
