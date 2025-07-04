import sys
import os
import json
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import zipfile
from datetime import datetime
import webbrowser
import winsound
import threading
from packaging.version import parse

# For Pillow >= 10
try:
    from PIL import Image, ImageTk, __version__ as PILLOW_VERSION
    Resampling = Image.Resampling
except AttributeError:
    # For older versions
    Resampling = Image

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)

def app_path():
    """Return the directory containing the running script or executable."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

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

        self.showing_popup = False  # Flag to track if popup is already shown

        # Create the menu bar
        self.menu_bar = tk.Menu(master)
        master.config(menu=self.menu_bar)

        # Create the File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Set Input Folder", command=self.select_input_folder)
        self.file_menu.add_command(label="Set Output Folder", command=self.select_output_folder)
        self.file_menu.add_command(label="Open Current Input Folder", command=self.open_input_folder)
        self.file_menu.add_command(label="Open Current Output Folder", command=self.open_output_folder)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=master.quit)

        # Create the Edit menu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo Last Crop", command=self.undo_last_crop)
        self.edit_menu.add_command(label="Zip Crops", command=self.zip_crops)

        # Create the View menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Preview Pane", command=lambda: self.toggle_pane("preview"))
        self.view_menu.add_command(label="Crops Pane", command=lambda: self.toggle_pane("crops"))
        self.view_menu.add_command(label="Sources Pane", command=lambda: self.toggle_pane("source"))

        # Create the Settings menu
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=self.settings_menu)
        self.auto_advance_var = tk.BooleanVar(value=False)
        self.crop_sound_var = tk.BooleanVar(value=False)
        self.show_welcome_var = tk.BooleanVar(value=True)
        self.safe_mode_var = tk.BooleanVar(value=False)
        self.default_input_folder = ""
        self.default_output_folder = ""
        self.settings_menu.add_checkbutton(label="Auto-advance", variable=self.auto_advance_var, command=self.save_settings)
        self.settings_menu.add_checkbutton(label="Crop Sound", variable=self.crop_sound_var, command=self.save_settings)
        self.settings_menu.add_command(label="Set Defaults", command=self.show_welcome_screen)

        # Create the Tools menu
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="PrunerIQ Analysis", command=self.launch_pruneriq)

        # Create the Help menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About", command=self.show_about)

        control_frame = tk.Frame(master)
        control_frame.pack(fill=tk.X, side=tk.TOP)

        tk.Label(control_frame, text="Select crop size:").pack(side=tk.LEFT, padx=(10, 2))
        
        self.size_var = tk.StringVar()
        self.custom_option = "Custom..."
        self.size_options = [
            "512x512",
            "768x768",
            "1024x1024",
            "2048x2048",
            "512x768",
            "768x512",
            self.custom_option,
        ]
        self.size_dropdown = ttk.Combobox(
            control_frame,
            textvariable=self.size_var,
            state="readonly",
            values=self.size_options,
        )
        self.size_dropdown.pack(side=tk.LEFT, padx=(2, 20))
        self.size_dropdown.set("512x512")  # Default size
        self.previous_size = "512x512"
        self.size_dropdown.bind("<<ComboboxSelected>>", self.on_size_selected)
        ToolTip(self.size_dropdown, "Choose the size of the crop area")

        self.prev_button = tk.Button(control_frame, text="< Prev", command=self.load_previous_image)
        self.prev_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.prev_button, "Load the previous image (S)")

        self.next_button = tk.Button(control_frame, text="Next >", command=self.load_next_image)
        self.next_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.next_button, "Load the next image (W)")

        # Load rotate left image
        try:
            self.rotate_left_image = tk.PhotoImage(file=resource_path("rotate_left.png"))
        except Exception as e:
            print(f"Error loading rotate_left.png: {e}")
            self.rotate_left_image = tk.PhotoImage()  # Placeholder if load fails

        # Load rotate right image
        try:
            self.rotate_right_image = tk.PhotoImage(file=resource_path("rotate_right.png"))
        except Exception as e:
            print(f"Error loading rotate_right.png: {e}")
            self.rotate_right_image = tk.PhotoImage()  # Placeholder if load fails

        self.rotate_left_button = tk.Button(control_frame, image=self.rotate_left_image, command=lambda: self.rotate_image(90))
        self.rotate_left_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.rotate_left_button, "Rotate image counterclockwise (A)")

        self.rotate_right_button = tk.Button(control_frame, image=self.rotate_right_image, command=lambda: self.rotate_image(-90))
        self.rotate_right_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.rotate_right_button, "Rotate image clockwise (D)")

        # Load delete image for the control frame
        try:
            self.delete_image = tk.PhotoImage(file=resource_path("delete_image.png"))
        except Exception as e:
            print(f"Error loading delete_image.png: {e}")
            self.delete_image = tk.PhotoImage()  # Placeholder if load fails

        self.delete_button = tk.Button(control_frame, image=self.delete_image, command=self.delete_current_image)
        self.delete_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.delete_button, "Delete the current image (Delete)")

        # Load folder icon for generic folder-related actions
        try:
            self.folder_icon = tk.PhotoImage(file=resource_path("folder.png"))
        except Exception as e:
            print(f"Error loading folder.png: {e}")
            self.folder_icon = tk.PhotoImage()

        # Load set input folder icon
        try:
            self.input_folder_icon = tk.PhotoImage(file=resource_path("input_folder.png"))
        except Exception as e:
            print(f"Error loading folder.png: {e}")
            self.input_folder_icon = tk.PhotoImage()

        # Load set output folder icon
        try:
            self.output_folder_icon = tk.PhotoImage(file=resource_path("output_folder.png"))
        except Exception as e:
            print(f"Error loading folder.png: {e}")
            self.output_folder_icon = tk.PhotoImage()

        # Load open output folder icon
        try:
            self.open_output_folder_icon = tk.PhotoImage(file=resource_path("open_folder.png"))
        except Exception as e:
            print(f"Error loading folder.png: {e}")
            self.open_output_folder_icon = tk.PhotoImage()

        # Set Input Folder button
        self.input_folder_button = tk.Button(control_frame, image=self.input_folder_icon, command=self.select_input_folder)
        self.input_folder_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.input_folder_button, "Set the input folder")

        # Set Output Folder button
        self.output_folder_button = tk.Button(control_frame, image=self.output_folder_icon, command=self.select_output_folder)
        self.output_folder_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.output_folder_button, "Set the output folder")

        # Open Output Folder button
        self.open_output_button = tk.Button(control_frame, image=self.open_output_folder_icon, command=self.open_output_folder)
        self.open_output_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.open_output_button, "Open the current output folder")

        # Undo Last Crop button (text based)
        self.undo_button = tk.Button(control_frame, text="Undo", command=self.undo_last_crop)
        self.undo_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.undo_button, "Undo the last crop (Ctrl+Z)")

        # Zip Crops button (text based)
        self.zip_button = tk.Button(control_frame, text="Zip", command=self.zip_crops)
        self.zip_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.zip_button, "Zip current folder crops into an archive")

        # Launch PrunerIQ button (text based)
        self.pruneriq_button = tk.Button(control_frame, text="PrunerIQ", command=self.launch_pruneriq)
        self.pruneriq_button.pack(side=tk.LEFT, padx=(10, 2))
        ToolTip(self.pruneriq_button, "Launch PrunerIQ analysis")

        self.image_counter_label = tk.Label(control_frame, text="Viewing 0 of 0")
        self.image_counter_label.pack(side=tk.RIGHT, padx=(10, 20))

        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_frame, cursor="cross", bg="gray")
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        self.preview_canvas = tk.Canvas(self.main_frame, width=512, height=512, bg="gray")
        self.preview_canvas.pack_forget()  # Hide preview pane initially

        # Create a frame for the crops pane with a scrollable canvas
        self.crops_frame = tk.Frame(self.main_frame)
        self.crops_canvas = tk.Canvas(self.crops_frame, bg="gray", width=512)  # Set width to match preview pane
        self.crops_scrollbar = tk.Scrollbar(self.crops_frame, orient="vertical", command=self.crops_canvas.yview)
        self.crops_canvas.configure(yscrollcommand=self.crops_scrollbar.set)
        self.crops_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.crops_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.crops_frame.pack_forget()  # Hide crops pane initially

        self.crops_canvas.bind("<Enter>", self.bind_crops_mouse_wheel)
        self.crops_canvas.bind("<Leave>", self.unbind_crops_mouse_wheel)

        # Create a frame for the source images pane with a scrollable canvas
        self.source_frame = tk.Frame(self.main_frame)
        self.source_canvas = tk.Canvas(self.source_frame, bg="gray", width=512)
        self.source_scrollbar = tk.Scrollbar(self.source_frame, orient="vertical", command=self.source_canvas.yview)
        self.source_canvas.configure(yscrollcommand=self.source_scrollbar.set)
        self.source_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.source_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.source_frame.pack_forget()  # Hide source pane initially

        self.source_canvas.bind("<Enter>", lambda e: self.source_canvas.bind_all("<MouseWheel>", self.on_source_mouse_wheel))
        self.source_canvas.bind("<Leave>", lambda e: self.source_canvas.unbind_all("<MouseWheel>"))

        self.status_bar = tk.Frame(master, bd=1, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_bar, text="Welcome to PixelPruner - Version 3.1.0", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10)
        self.cropped_images_label = tk.Label(self.status_bar, text="Images Cropped: 0", anchor=tk.E)
        self.cropped_images_label.pack(side=tk.RIGHT, padx=10)

        self.folder_path = None
        self.images = []
        self.image_index = 0
        self.current_image = None
        self.image_scale = 1
        self.rect = None
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.output_folder = None
        self.original_size = (512, 512)
        self.current_size = (512, 512)
        self.crop_counter = 0  # Global counter for all crops
        self.cropped_images = []  # List to keep track of cropped images
        self.cropped_thumbnails = []  # List to keep track of cropped thumbnails
        self.source_thumbnails = []  # Thumbnails for source images
        self.preview_enabled = False  # Preview pane toggle
        self.crops_enabled = False  # Crop thumbnails pane toggle
        self.source_enabled = False  # Source images pane toggle

        # Load delete image for the crops pane
        try:
            self.delete_crop_image = tk.PhotoImage(file=resource_path("delete_crop.png"))
        except Exception as e:
            print(f"Error loading delete_crop.png: {e}")
            self.delete_crop_image = tk.PhotoImage()  # Placeholder if load fails

        # Enable drag-and-drop for the main frame
        self.main_frame.drop_target_register(DND_FILES)
        self.main_frame.dnd_bind('<<Drop>>', self.on_drop)

        # Update the window and canvas sizes before displaying the first image
        self.master.update_idletasks()
        self.canvas.update_idletasks()

        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        # Track window state to resize images when the window is maximized or restored
        self.last_state = self.master.state()
        self.master.bind("<Configure>", self.on_window_resize)

        self.master.minsize(1300, 750)  # Set a minimum size for the window

        # Bind keyboard shortcuts
        self.master.bind("w", lambda event: self.load_next_image())
        self.master.bind("s", lambda event: self.load_previous_image())
        self.master.bind("a", lambda event: self.rotate_image(90))
        self.master.bind("d", lambda event: self.rotate_image(-90))
        self.master.bind("<Control-z>", lambda event: self.undo_last_crop())
        self.master.bind("<Delete>", lambda event: self.delete_current_image())

        # Set the focus to the master window
        master.focus_set()

        # Load user settings and apply them
        self.load_settings()
        self.update_safe_mode_ui()
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # Center the window on the screen
        self.center_window()

        if self.show_welcome_var.get():
            self.show_welcome_screen()

    def center_window(self):
        self.master.update_idletasks()
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.master.geometry(f'{window_width}x{window_height}+{x}+{y}')

    def update_status(self, message):
        self.status_label.config(text=message)

    def update_image_counter(self):
        self.image_counter_label.config(text=f"Viewing {self.image_index + 1} of {len(self.images)}")

    def update_cropped_images_counter(self):
        self.cropped_images_label.config(text=f"Images Cropped: {len(self.cropped_images)}")

    def show_info_message(self, title, message):
        if not self.showing_popup:
            self.showing_popup = True
            messagebox.showinfo(title, message)
            self.showing_popup = False

    def update_safe_mode_ui(self):
        """Enable or disable delete-related widgets based on safe mode."""
        state = tk.DISABLED if self.safe_mode_var.get() else tk.NORMAL
        self.delete_button.config(state=state)
        self.undo_button.config(state=state)
        # Update Edit menu entry for Undo Last Crop
        try:
            self.edit_menu.entryconfig("Undo Last Crop", state=state)
        except Exception:
            pass

    def on_window_resize(self, event):
        """Redraw the image when the window is resized or state changes."""
        if event.widget is self.master and self.current_image:
            # Only redraw when the zoom state or canvas size changes
            state = self.master.state()
            if state != self.last_state or event.width != self.canvas.winfo_width() or event.height != self.canvas.winfo_height():
                self.last_state = state
                self.display_image()

    def load_image(self):
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please select an input folder.")
            return
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

        # Determine available canvas space. When the window is maximized
        # ("zoomed" state on Windows), use the full canvas size. Otherwise
        # limit the image to the default 800x600 viewing area.
        is_zoomed = self.master.state() == "zoomed"
        max_w = self.canvas.winfo_width() if is_zoomed else 800
        max_h = self.canvas.winfo_height() if is_zoomed else 600

        self.scaled_width = min(self.current_image.width, max_w)
        self.scaled_height = int(self.scaled_width / aspect_ratio)
        if self.scaled_height > max_h:
            self.scaled_height = min(self.current_image.height, max_h)
            self.scaled_width = int(self.scaled_height * aspect_ratio)
        
        resampling_filter = Resampling.LANCZOS
        
        self.tkimage = ImageTk.PhotoImage(self.current_image.resize((self.scaled_width, self.scaled_height), resampling_filter))

        # Center the image within the canvas
        self.center_image_on_canvas()

        self.canvas.delete("all")
        self.canvas.create_image(self.image_offset_x, self.image_offset_y, anchor="nw", image=self.tkimage)
        self.image_scale = self.current_image.width / self.scaled_width
        size = tuple(map(int, self.size_var.get().split('x')))
        self.original_size = size
        self.current_size = size
        scaled_size = (int(size[0] / self.image_scale), int(size[1] / self.image_scale))  # Scale crop box to match displayed image
        self.rect = self.canvas.create_rectangle(self.image_offset_x, self.image_offset_y, self.image_offset_x + scaled_size[0], self.image_offset_y + scaled_size[1], outline='red')
        self.update_crop_box_size()
        self.update_image_counter()

    def center_image_on_canvas(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.image_offset_x = (canvas_width - self.scaled_width) // 2
        self.image_offset_y = (canvas_height - self.scaled_height) // 2

    def rotate_image(self, angle):
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return
        if self.current_image:
            self.current_image = self.current_image.rotate(angle, expand=True)
            self.display_image()
            self.update_status(f"Image rotated by {angle} degrees")

    def on_size_selected(self, event=None):
        selection = self.size_var.get()
        if selection == self.custom_option:
            # restore previous size while dialog is open
            self.size_var.set(self.previous_size)
            self.open_custom_size_dialog()
        else:
            self.previous_size = selection
            self.update_crop_box_size()

    def open_custom_size_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("Custom Size")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()

        width_var = tk.StringVar(value=str(self.current_size[0]))
        height_var = tk.StringVar(value=str(self.current_size[1]))

        tk.Label(dialog, text="Width:").grid(row=0, column=0, padx=10, pady=(10, 5))
        width_entry = tk.Entry(dialog, textvariable=width_var, width=10)
        width_entry.grid(row=0, column=1, padx=10, pady=(10, 5))

        tk.Label(dialog, text="Height:").grid(row=1, column=0, padx=10, pady=5)
        height_entry = tk.Entry(dialog, textvariable=height_var, width=10)
        height_entry.grid(row=1, column=1, padx=10, pady=5)

        def apply():
            try:
                w = int(width_var.get())
                h = int(height_var.get())
                if w <= 0 or h <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter positive integers for width and height.")
                return
            value = f"{w}x{h}"
            values = list(self.size_dropdown["values"])
            if value not in values:
                values.insert(-1, value)
                self.size_dropdown["values"] = values
            self.size_var.set(value)
            self.previous_size = value
            self.update_crop_box_size()
            dialog.destroy()

        def cancel():
            self.size_var.set(self.previous_size)
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(5, 10))
        tk.Button(btn_frame, text="OK", command=apply).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)

        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        dialog.geometry(f"{w}x{h}+{sw//2 - w//2}+{sh//2 - h//2}")

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

            # Parse desired output size
            target_width, target_height = self.original_size

            # Set max size for preview pane display
            preview_max = 512
            aspect_ratio = target_width / target_height

            if aspect_ratio >= 1:
                preview_w = preview_max
                preview_h = int(preview_w / aspect_ratio)
            else:
                preview_h = preview_max
                preview_w = int(preview_h * aspect_ratio)

            cropped = cropped.resize((preview_w, preview_h), Resampling.LANCZOS)
            self.tkpreview = ImageTk.PhotoImage(cropped)

            self.preview_canvas.delete("all")
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            offset_x = (canvas_w - preview_w) // 2
            offset_y = (canvas_h - preview_h) // 2

            self.preview_canvas.create_image(offset_x, offset_y, anchor="nw", image=self.tkpreview)


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

    def on_source_mouse_wheel(self, event):
        self.source_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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

        # Prompt for output folder if not set and images are dragged in
        if not self.output_folder and not self.folder_path:
            self.select_output_folder()
            if not self.output_folder:
                self.show_info_message("Information", "Please set an Output Folder from the File Menu!")
                return

        # Use input folder as output folder if set and output folder is not set
        if not self.output_folder:
            self.output_folder = self.folder_path

        # Generate a unique filename by appending a global counter
        self.crop_counter += 1
        image_path = self.images[self.image_index]
        base_filename = os.path.basename(image_path)
        filename, ext = os.path.splitext(base_filename)
        cropped_filename = f"cropped_{self.crop_counter}_{filename}.png"
        cropped_filepath = os.path.join(self.output_folder, cropped_filename)
        cropped.save(cropped_filepath, "PNG")
        self.cropped_images.insert(0, cropped_filepath)  # Insert at the beginning of the list
        self.update_cropped_images_counter()

        # Play crop sound if enabled
        if self.crop_sound_var.get():
            winsound.PlaySound(resource_path("click.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)

        # Create thumbnail and update crops canvas
        self.update_crops_canvas(cropped, cropped_filepath)
        cropped_filepath = os.path.join(self.output_folder, cropped_filename)
        normalized_path = os.path.normpath(cropped_filepath)
        self.update_status(f"Cropped image saved as {normalized_path}")

    def update_crops_canvas(self, cropped, filepath):
        cropped.thumbnail((256, 256))  # Create larger thumbnail
        tkthumbnail = ImageTk.PhotoImage(cropped)
        self.cropped_thumbnails.insert(0, (tkthumbnail, filepath))  # Insert at the beginning of the list

        self.refresh_crops_canvas()

    def refresh_crops_canvas(self):
        """Rebuild the thumbnail grid in the crops canvas."""
        self.crops_canvas.delete("all")  # Clear previous thumbnails
        cols = 2  # Number of columns in the grid
        spacing = 10  # Space between thumbnails

        for index, (thumbnail, path) in enumerate(self.cropped_thumbnails):
            row, col = divmod(index, cols)
            x, y = col * (256 + spacing), row * (256 + spacing)
            self.crops_canvas.create_image(x, y, anchor="nw", image=thumbnail)

            # Add delete icon at the bottom left corner of each thumbnail
            delete_icon_x = x + 5
            delete_icon_y = y + 256 - 25
            delete_icon = self.crops_canvas.create_image(delete_icon_x, delete_icon_y, anchor="nw", image=self.delete_crop_image)
            self.crops_canvas.tag_bind(delete_icon, "<Button-1>", lambda event, path=path: self.delete_crop(path))

        # Update scroll region to accommodate all thumbnails
        self.crops_canvas.config(scrollregion=self.crops_canvas.bbox("all"))

    def delete_crop(self, filepath):
        if self.safe_mode_var.get():
            self.show_info_message("Safe Mode", "Safe Mode is enabled. Delete operations are disabled.")
            return
        if messagebox.askyesno("Delete Crop", "Are you sure you want to delete this crop?"):
            if os.path.exists(filepath):
                os.remove(filepath)
            self.cropped_images = [img for img in self.cropped_images if img != filepath]
            self.cropped_thumbnails = [(thumb, path) for thumb, path in self.cropped_thumbnails if path != filepath]
            filepath_forward_slash = filepath.replace("\\", "/")
            self.refresh_crops_canvas()
            self.update_cropped_images_counter()
            self.update_status(f"Deleted crop {filepath_forward_slash}")

    def update_crops_canvas_layout(self):
        """Legacy wrapper kept for backward compatibility."""
        self.refresh_crops_canvas()

    def update_source_canvas(self, progress_callback=None):
        """Generate thumbnails for source images and rebuild the gallery."""
        self.source_thumbnails = []
        total = len(self.images)
        for idx, path in enumerate(self.images, start=1):
            try:
                img = Image.open(path)
                img.thumbnail((128, 128))
                tkthumb = ImageTk.PhotoImage(img)
                self.source_thumbnails.append((tkthumb, path))
            except Exception:
                continue
            if progress_callback:
                progress_callback(idx, total)
        self.refresh_source_canvas()

    def refresh_source_canvas(self):
        self.source_canvas.delete("all")
        self.source_canvas.update_idletasks()
        canvas_width = self.source_canvas.winfo_width()
        cols = 3
        spacing = 10
        thumb_w = 128
        total_width = cols * thumb_w + (cols - 1) * spacing
        offset_x = max(0, (canvas_width - total_width) // 2)
        for index, (thumb, path) in enumerate(self.source_thumbnails):
            row, col = divmod(index, cols)
            x = offset_x + col * (thumb_w + spacing)
            y = row * (128 + spacing)
            img_id = self.source_canvas.create_image(x, y, anchor="nw", image=thumb)
            self.source_canvas.tag_bind(img_id, "<Button-1>", lambda e, p=path: self.load_image_from_gallery(p))
        self.source_canvas.config(scrollregion=self.source_canvas.bbox("all"))

    def load_image_from_gallery(self, path):
        if path in self.images:
            self.image_index = self.images.index(path)
            self.load_image()

    def perform_crop(self):
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return
        x1, y1, x2, y2 = self.canvas.coords(self.rect)
        self.crop_image(x1, y1, x2, y2)
        if self.auto_advance_var.get():
            self.load_next_image()

    def load_next_image(self):
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return

        if not self.images:
            self.show_info_message("Information", "No images loaded.")
            return

        self.image_index = (self.image_index + 1) % len(self.images)
        self.load_image()

    def load_previous_image(self):
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return

        if not self.images:
            self.show_info_message("Information", "No images loaded.")
            return

        self.image_index = (self.image_index - 1) % len(self.images)
        self.load_image()

    def select_input_folder(self):
        selected_folder = filedialog.askdirectory(title="Select Input Folder", initialdir=self.default_input_folder or None)
        if selected_folder:
            self.folder_path = selected_folder
            self.load_images_from_folder()
        else:
            messagebox.showwarning("Warning", "No input folder selected!")

    def select_output_folder(self):
        selected_folder = filedialog.askdirectory(title="Select Custom Output Folder", initialdir=self.default_output_folder or None)
        if selected_folder:
            self.output_folder = selected_folder
        else:
            messagebox.showwarning("Warning", "No output folder selected! Crops can't be saved until one is set!")

    def open_input_folder(self):
        if not self.folder_path:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return
        if os.path.isdir(self.folder_path):
            subprocess.Popen(['explorer', self.folder_path.replace("/", "\\")])

    def open_output_folder(self):
        folder_to_open = self.output_folder or self.folder_path
        if not folder_to_open:
            self.show_info_message("Information", "Please set an Output Folder from the File Menu!")
            return
        if os.path.isdir(folder_to_open):
            subprocess.Popen(['explorer', folder_to_open.replace("/", "\\")])

    def zip_crops(self):
        if not self.cropped_images:
            messagebox.showinfo("Info", "No cropped images to zip!")
            return

        num_images = len(self.cropped_images)
        current_date = datetime.now().strftime("%Y%m%d")
        zip_filename = os.path.join(self.output_folder or self.folder_path, f"{num_images}_{current_date}.zip").replace("\\", "/")

        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in self.cropped_images:
                zipf.write(file, os.path.basename(file))

        messagebox.showinfo("Info", f"Cropped images have been zipped into {zip_filename}")
        self.update_status(f"{num_images} cropped images zipped into {zip_filename}")

    def toggle_pane(self, pane):
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return

        if pane == "preview":
            self.preview_enabled = not self.preview_enabled
            self.crops_enabled = False
            self.source_enabled = False
        elif pane == "crops":
            self.crops_enabled = not self.crops_enabled
            self.preview_enabled = False
            self.source_enabled = False
        elif pane == "source":
            self.source_enabled = not self.source_enabled
            self.preview_enabled = False
            self.crops_enabled = False

        if self.preview_enabled:
            self.master.geometry(f"1550x800")  # Adjusted size to fit the larger preview pane
            self.preview_canvas.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=False)
            self.crops_frame.pack_forget()
            self.source_frame.pack_forget()
        elif self.crops_enabled:
            self.master.geometry(f"1550x800")  # Adjusted size to fit the crops pane
            self.crops_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=False)
            self.preview_canvas.pack_forget()
            self.source_frame.pack_forget()
        elif self.source_enabled:
            self.master.geometry(f"1550x800")
            self.source_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=False)
            self.preview_canvas.pack_forget()
            self.crops_frame.pack_forget()
        else:
            self.preview_canvas.pack_forget()
            self.crops_frame.pack_forget()
            self.source_frame.pack_forget()
            self.master.geometry(f"1300x750")  # Resize the window back to normal
        
        # Workaround to ensure the main image is centered after toggling panes
        self.master.after(100, self.load_next_image)
        self.master.after(200, self.load_previous_image)

    def undo_last_crop(self):
        if self.safe_mode_var.get():
            self.show_info_message("Safe Mode", "Safe Mode is enabled. Delete operations are disabled.")
            return
        if not self.cropped_images:
            messagebox.showinfo("Info", "No cropped images to undo!")
            return

        last_cropped_image = self.cropped_images.pop(0)  # Remove the first item in the list
        if os.path.exists(last_cropped_image):
            os.remove(last_cropped_image)

        self.cropped_thumbnails.pop(0)
        self.refresh_crops_canvas()
        self.update_cropped_images_counter()
        self.update_status("Last crop undone")

    def load_images_from_folder(self):
        if not self.folder_path:
            messagebox.showwarning("Warning", f"No input folder set! Got: {self.folder_path}")
            return

        self.images = [os.path.join(self.folder_path, img) for img in os.listdir(self.folder_path) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not self.images:
            messagebox.showerror("Error", "No valid images found in the selected directory.")
            return

        progress = None
        progress_var = None
        if len(self.images) > 30:
            progress = tk.Toplevel(self.master)
            progress.title("Loading")
            tk.Label(progress, text="Loading images...").pack(padx=20, pady=(10, 5))
            progress_var = tk.StringVar(value="")
            tk.Label(progress, textvariable=progress_var).pack(padx=20, pady=(0, 10))
            progress.update_idletasks()
            pw = progress.winfo_width()
            ph = progress.winfo_height()
            sw = progress.winfo_screenwidth()
            sh = progress.winfo_screenheight()
            progress.geometry(f"{pw}x{ph}+{sw//2 - pw//2}+{sh//2 - ph//2}")
            progress.transient(self.master)
            progress.grab_set()

            def cb(idx, total):
                progress_var.set(f"{idx} of {total}")
                progress.update_idletasks()
        else:
            def cb(idx, total):
                pass

        self.image_index = 0
        self.load_image()
        self.update_image_counter()
        self.update_status(f"Loaded {len(self.images)} images from {self.folder_path}")
        self.update_source_canvas(cb)
        if progress:
            progress.destroy()

    def load_images_from_list(self, file_list):
        self.images = [file for file in file_list if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not self.images:
            messagebox.showerror("Error", "No valid images found in the dropped files.")
            return

        progress = None
        progress_var = None
        if len(self.images) > 30:
            progress = tk.Toplevel(self.master)
            progress.title("Loading")
            tk.Label(progress, text="Loading images...").pack(padx=20, pady=(10, 5))
            progress_var = tk.StringVar(value="")
            tk.Label(progress, textvariable=progress_var).pack(padx=20, pady=(0, 10))
            progress.update_idletasks()
            pw = progress.winfo_width()
            ph = progress.winfo_height()
            sw = progress.winfo_screenwidth()
            sh = progress.winfo_screenheight()
            progress.geometry(f"{pw}x{ph}+{sw//2 - pw//2}+{sh//2 - ph//2}")
            progress.transient(self.master)
            progress.grab_set()

            def cb(idx, total):
                progress_var.set(f"{idx} of {total}")
                progress.update_idletasks()
        else:
            def cb(idx, total):
                pass

        self.image_index = 0
        self.load_image()
        self.update_image_counter()
        self.update_status(f"Loaded {len(self.images)} images from dropped files")
        self.update_source_canvas(cb)
        if progress:
            progress.destroy()

    def on_drop(self, event):
        file_list = self.master.tk.splitlist(event.data)
        self.load_images_from_list(file_list)

    def view_image(self, image_path):
        """Display an image on the canvas without altering the loaded list."""
        if not image_path or not os.path.exists(image_path):
            return
        try:
            self.current_image = Image.open(image_path)
            self.image_scale = 1
            self.display_image()
            self.update_status(f"Viewing {os.path.basename(image_path)}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load {image_path}: {exc}")

    def toggle_auto_advance(self):
        self.auto_advance_var.set(not self.auto_advance_var.get())

    def delete_current_image(self):
        if self.safe_mode_var.get():
            self.show_info_message("Safe Mode", "Safe Mode is enabled. Delete operations are disabled.")
            return
        if not self.folder_path and not self.images:
            self.show_info_message("Information", "Please set an Input Folder from the File Menu!")
            return
        if messagebox.askyesno("Delete Image", "Are you sure you want to delete this image?"):
            image_path = self.images.pop(self.image_index)
            if os.path.exists(image_path):
                os.remove(image_path)
            if self.image_index >= len(self.images):
                self.image_index = 0
            self.load_image()
            self.update_image_counter()
            # Remove from source thumbnails and refresh gallery
            self.source_thumbnails = [(t, p) for t, p in self.source_thumbnails if p != image_path]
            self.refresh_source_canvas()
            image_path_forward_slash = image_path.replace("\\", "/")
            self.update_status(f"Deleted image {image_path_forward_slash}")

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
            "Version 3.1.0 - 6/11/2025\n\n"
            "Developed by TheAlly and GPT4o\n\n"
            "About: Prepare your LoRA training data with ease! "
            "Check out the GitHub Repo for the full feature list.\n\n"
        )
        
        label = tk.Label(about_window, text=about_text, justify=tk.LEFT, padx=10, pady=10, wraplength=380)
        label.pack(fill="both", expand=True)

        link_frame = tk.Frame(about_window)
        link_frame.pack(fill="both", expand=True)

        profile_label = tk.Label(link_frame, text="GitHub:", justify=tk.LEFT, padx=10)
        profile_label.pack(side=tk.LEFT)
        link = tk.Label(link_frame, text="https://github.com/theallyprompts/PixelPruner", fg="blue", cursor="hand2", padx=10)
        link.pack(side=tk.LEFT)
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/theallyprompts/PixelPruner"))

    def show_welcome_screen(self):
        welcome = tk.Toplevel(self.master)
        welcome.title("Welcome to PixelPruner")
        welcome.geometry("520x380")
        welcome.resizable(False, False)
        welcome.protocol("WM_DELETE_WINDOW", lambda: None)
        welcome.overrideredirect(True)
        welcome.grab_set()

        # Center it
        welcome.update_idletasks()
        w = welcome.winfo_width()
        h = welcome.winfo_height()
        sw = welcome.winfo_screenwidth()
        sh = welcome.winfo_screenheight()
        welcome.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        frame = tk.Frame(welcome, padx=20, pady=20)
        frame.pack(expand=True, fill="both")

        tk.Label(frame, text="Welcome to PixelPruner!", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        tk.Label(frame, text="Crop, curate, and conquer your datasets.\n", justify="center").pack()

        link = tk.Label(frame, text="View on GitHub", fg="blue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/theallyprompts/PixelPruner"))

        donate = tk.Label(frame, text="Buy me a coffee ☕", fg="blue", cursor="hand2")
        donate.pack(pady=(5, 15))
        donate.bind("<Button-1>", lambda e: webbrowser.open_new("https://ko-fi.com/theallyprompts"))

        # Input Folder
        tk.Label(frame, text="Default Input Folder:").pack(anchor="w")
        input_row = tk.Frame(frame)
        input_row.pack(fill="x")
        input_entry = tk.Entry(input_row, width=50)
        input_entry.insert(0, self.settings.get("default_input_folder", ""))
        input_entry.pack(side="left", fill="x", expand=True)
        tk.Button(input_row, text="Select Folder", command=lambda: self._browse_folder(input_entry)).pack(side="right")

        # Output Folder
        tk.Label(frame, text="Default Output Folder:").pack(anchor="w", pady=(10, 0))
        output_row = tk.Frame(frame)
        output_row.pack(fill="x")
        output_entry = tk.Entry(output_row, width=50)
        output_entry.insert(0, self.settings.get("default_output_folder", ""))
        output_entry.pack(side="left", fill="x", expand=True)
        tk.Button(output_row, text="Select Folder", command=lambda: self._browse_folder(output_entry)).pack(side="right")

        # Footer controls
        footer = tk.Frame(frame)
        footer.pack(fill="x", pady=(20, 0), padx=10)

        left_footer = tk.Frame(footer)
        left_footer.pack(side="left")

        show_var = tk.BooleanVar(value=self.settings.get("show_welcome", True))
        tk.Checkbutton(left_footer, text="Show Welcome at startup", variable=show_var).pack(side="left")
        
        safe_var = tk.BooleanVar(value=self.settings.get("safe_mode", False))
        tk.Checkbutton(left_footer, text="Safe Mode - Delete actions disabled", variable=safe_var).pack(side="left", padx=(10, 0))

        def save_and_close():
            self.settings["show_welcome"] = show_var.get()
            self.show_welcome_var.set(show_var.get())            
            self.settings["default_input_folder"] = input_entry.get()
            self.settings["default_output_folder"] = output_entry.get()
            self.settings["safe_mode"] = safe_var.get()
            self.safe_mode_var.set(safe_var.get())
            self.default_input_folder = input_entry.get()
            self.default_output_folder = output_entry.get()
            self.folder_path = self.default_input_folder
            self.output_folder = self.default_output_folder
            self.save_settings()
            self.folder_path = input_entry.get()
            self.output_folder = output_entry.get()
            if self.folder_path:
                self.load_images_from_folder()
            self.update_status("Ready.")
            self.update_safe_mode_ui()
            welcome.destroy()

        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=(15, 10))

        tk.Button(button_frame, text="Start Using PixelPruner", command=save_and_close).pack(side="top", anchor="center")

    def _browse_folder(self, entry_widget):
        path = filedialog.askdirectory(title="Select Folder")
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def load_settings(self):
        #Load settings from usersettings.json, creating it with defaults if needed.
        self.settings_path = os.path.join(app_path(), "usersettings.json")
        defaults = {
            "auto_advance": False,
            "crop_sound": False,
            "show_welcome": True,
            "safe_mode": False,
            "default_input_folder": "",
            "default_output_folder": "",
        }
        if not os.path.exists(self.settings_path):
            self.settings = defaults
            self.save_settings()
            return
        try:
            with open(self.settings_path, "r") as f:
                self.settings = json.load(f)
        except Exception:
            self.settings = defaults
        self.auto_advance_var.set(self.settings.get("auto_advance", False))
        self.crop_sound_var.set(self.settings.get("crop_sound", False))
        self.show_welcome_var.set(self.settings.get("show_welcome", True))
        self.safe_mode_var.set(self.settings.get("safe_mode", False))
        self.default_input_folder = self.settings.get("default_input_folder", "")
        self.default_output_folder = self.settings.get("default_output_folder", "")

        if self.default_input_folder and os.path.isdir(self.default_input_folder):
            self.folder_path = self.default_input_folder
        if self.default_output_folder and os.path.isdir(self.default_output_folder):
            self.output_folder = self.default_output_folder

    def save_settings(self):
        # Update self.settings dict from current UI values
        self.settings["auto_advance"] = self.auto_advance_var.get()
        self.settings["crop_sound"] = self.crop_sound_var.get()
        self.settings["show_welcome"] = self.show_welcome_var.get()
        self.settings["safe_mode"] = self.safe_mode_var.get()
        self.settings["default_input_folder"] = self.default_input_folder
        self.settings["default_output_folder"] = self.default_output_folder

        try:
            with open(os.path.join(app_path(), "usersettings.json"), "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def launch_pruneriq(self):
        from pruneriq import analyze_folder
        if not self.output_folder:
            self.show_info_message("Information", "Please set or create an Output Folder first!")
            return

        folder = self.output_folder

        loading = tk.Toplevel(self.master)
        loading.title("Please Wait")
        tk.Label(loading, text="Analyzing images...").pack(padx=20, pady=20)
        loading.update()

        results = []

        def run_analysis():
            nonlocal results
            results = analyze_folder(folder, True)
            self.master.after(0, finish)

        def finish():
            loading.destroy()
            self.show_analysis_results(results, folder)

        threading.Thread(target=run_analysis, daemon=True).start()


    def show_analysis_results(self, results, folder_path):
        from pruneriq import analyze_folder
        if not results:
            self.show_info_message(
                "Analysis",
                "No valid images were found in the selected output folder.",
            )
            return

        window = tk.Toplevel(self.master)
        window.title("PrunerIQ - Dataset Analysis")
        window.geometry("900x500")

        window.update_idletasks()
        window_width = window.winfo_width()
        window_height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        current_folder = folder_path
        path_var = tk.StringVar(value=current_folder)

        path_frame = tk.Frame(window)
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(path_frame, text="Analyzing Images in:").pack(side=tk.LEFT)
        tk.Label(path_frame, textvariable=path_var, anchor="w").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        crops_only_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            path_frame,
            text="Crops Only",
            variable=crops_only_var,
        ).pack(side=tk.RIGHT, padx=5)

        def run_analysis(path):
            nonlocal all_results, current_folder
            current_folder = path
            path_var.set(path)

            progress = tk.Toplevel(window)
            progress.title("Analyzing")
            tk.Label(progress, text="Analyzing images...").pack(padx=20, pady=(10, 5))
            progress_var = tk.StringVar(value="")
            tk.Label(progress, textvariable=progress_var).pack(padx=20, pady=(0, 10))

            progress.update_idletasks()
            pw = progress.winfo_width()
            ph = progress.winfo_height()
            sx = progress.winfo_screenwidth()
            sy = progress.winfo_screenheight()
            progress.geometry(f"{pw}x{ph}+{sx//2 - pw//2}+{sy//2 - ph//2}")
            progress.transient(window)
            progress.grab_set()

            def progress_callback(idx, total):
                window.after(0, lambda: progress_var.set(f"{idx} of {total}"))

            def worker():
                res = analyze_folder(path, crops_only_var.get(), progress_callback)
                window.after(0, lambda: finish(res))

            def finish(res):
                progress.destroy()
                nonlocal all_results
                all_results = res
                populate_tree(all_results)
                update_summary()

            threading.Thread(target=worker, daemon=True).start()

        def change_folder():
            path = filedialog.askdirectory(title="Select Folder")
            if path:
                run_analysis(path)

        def manual_reanalyze():
            run_analysis(current_folder)

        def open_current_folder():
            if os.path.isdir(current_folder):
                subprocess.Popen([
                    "explorer",
                    current_folder.replace("/", "\\"),
                ])

        tk.Button(path_frame, text="Change Folder", command=change_folder).pack(
            side=tk.RIGHT, padx=5
        )
        tk.Button(path_frame, text="Open Folder", command=open_current_folder).pack(
            side=tk.RIGHT, padx=5
        )
        tk.Button(path_frame, text="Re-analyze", command=manual_reanalyze).pack(
            side=tk.RIGHT, padx=5
        )

        columns = (
            "filename",
            "contrast",
            "clarity",
            "noise",
            "rating",
        )
        tree_frame = tk.Frame(window)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_scrollbar = tk.Scrollbar(tree_frame, orient="vertical")
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=tree_scrollbar.set,
        )
        tree_scrollbar.config(command=tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        all_results = results
        explanations = {}

        def sort_tree(col, reverse):
            data = [(tree.set(k, col), k) for k in tree.get_children("")]
            if col in ("filename", "rating"):
                data.sort(reverse=reverse)
            else:
                data.sort(key=lambda t: float(t[0]), reverse=reverse)
            for index, (val, k) in enumerate(data):
                tree.move(k, "", index)
            tree.heading(col, command=lambda: sort_tree(col, not reverse))

        col_widths = {
            "filename": 200,
            "contrast": 110,
            "clarity": 110,
            "noise": 110,
            "rating": 80,
        }

        heading_names = {
            "contrast": "Contrast (%)",
            "clarity": "Clarity (%)",
            "noise": "Noise (%)",
        }

        for col in columns:
            text = heading_names.get(col, col.title())
            tree.heading(col, text=text, command=lambda c=col: sort_tree(c, False))
            anchor = "w" if col == "filename" else "center"
            width = col_widths.get(col, 100)
            tree.column(col, anchor=anchor, width=width, stretch=False)

        def populate_tree(items):
            tree.delete(*tree.get_children())
            explanations.clear()
            for result in items:
                item = tree.insert(
                    "",
                    "end",
                    values=(
                        result["filename"],
                        f"{result['contrast']:.2f} ({result['contrast_pct']:.0f}%)",
                        f"{result['clarity']:.2f} ({result['clarity_pct']:.0f}%)",
                        f"{result['noise']:.2f} ({result['noise_pct']:.0f}%)",
                        result["rating"],
                    ),
                )
                explanations[item] = result.get("reason", "")

        populate_tree(all_results)

        filter_frame = tk.Frame(window)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        entries = {}
        metrics = ["contrast", "clarity", "noise"]
        for i, metric in enumerate(metrics):
            tk.Label(filter_frame, text=f"{metric.title()} Min").grid(row=0, column=i*2, sticky="e")
            e_min = tk.Entry(filter_frame, width=6)
            e_min.grid(row=0, column=i*2+1, sticky="w")
            tk.Label(filter_frame, text=f"Max").grid(row=1, column=i*2, sticky="e")
            e_max = tk.Entry(filter_frame, width=6)
            e_max.grid(row=1, column=i*2+1, sticky="w")
            entries[metric] = (e_min, e_max)

        tk.Label(filter_frame, text="Rating").grid(row=0, column=6, sticky="e")
        rating_var = tk.StringVar(value="All")
        rating_box = ttk.Combobox(filter_frame, textvariable=rating_var, state="readonly",
                                 values=["All", "Poor", "Fair", "Good", "Excellent"])
        rating_box.grid(row=0, column=7, sticky="w")

        info_label = tk.Label(window, text="", anchor="w")
        info_label.pack(fill=tk.X, padx=5)

        def apply_filter():
            filtered = []
            for r in all_results:
                passes = True
                for metric in metrics:
                    min_val = entries[metric][0].get()
                    max_val = entries[metric][1].get()
                    value = r[metric]
                    if min_val:
                        try:
                            if value < float(min_val):
                                passes = False
                                break
                        except ValueError:
                            pass
                    if max_val:
                        try:
                            if value > float(max_val):
                                passes = False
                                break
                        except ValueError:
                            pass
                if rating_var.get() != "All" and r["rating"] != rating_var.get():
                    passes = False
                if passes:
                    filtered.append(r)
            populate_tree(filtered)

        def reset_filter():
            for metric in metrics:
                entries[metric][0].delete(0, tk.END)
                entries[metric][1].delete(0, tk.END)
            rating_var.set("All")
            populate_tree(all_results)

        tk.Button(filter_frame, text="Apply Filter", command=apply_filter).grid(row=0, column=8, padx=5)
        tk.Button(filter_frame, text="Reset", command=reset_filter).grid(row=1, column=8, padx=5)

        def on_select(event):
            selected = tree.selection()
            if selected:
                info_label.config(text=explanations.get(selected[0], ""))

        tree.bind("<<TreeviewSelect>>", on_select)

        def delete_selected():
            if self.safe_mode_var.get():
                self.show_info_message(
                    "Safe Mode",
                    "Safe Mode is enabled. Delete operations are disabled.",
                )
                return
            for item in tree.selection():
                filename = tree.set(item, "filename")
                path = os.path.join(current_folder, filename)
                if os.path.exists(path):
                    os.remove(path)
                tree.delete(item)

        def on_double_click(event):
            item = tree.focus()
            if item:
                filename = tree.set(item, "filename")
                path = os.path.join(current_folder, filename)
                self.view_image(path)

        tree.bind("<Double-1>", on_double_click)

        button_frame = tk.Frame(window)
        button_frame.pack(fill=tk.X, pady=5)
        tk.Button(button_frame, text="Delete Selected", command=delete_selected).pack(
            side=tk.RIGHT, padx=5
        )

        summary_label = tk.Label(
            window, font=("Helvetica", 10), anchor="w", justify="left"
        )
        summary_label.pack(padx=10, pady=10, anchor="w")

        def update_summary():
            if not all_results:
                summary = "Images: 0"
            else:
                avg_contrast = sum(r["contrast"] for r in all_results) / len(all_results)
                avg_clarity = sum(r["clarity"] for r in all_results) / len(all_results)
                avg_noise = sum(r["noise"] for r in all_results) / len(all_results)
                avg_contrast_pct = sum(r["contrast_pct"] for r in all_results) / len(all_results)
                avg_clarity_pct = sum(r["clarity_pct"] for r in all_results) / len(all_results)
                avg_noise_pct = sum(r["noise_pct"] for r in all_results) / len(all_results)
                summary = (
                    f"Images: {len(all_results)}\n"
                    f"Avg Contrast: {avg_contrast:.2f} ({avg_contrast_pct:.0f}%)   "
                    f"Avg Clarity: {avg_clarity:.2f} ({avg_clarity_pct:.0f}%)   "
                    f"Avg Noise: {avg_noise:.2f} ({avg_noise_pct:.0f}%)"
                )
            summary_label.config(text=summary)

        update_summary()


    def on_close(self):
        """Handle application close."""
        self.save_settings()
        self.master.destroy()

def main():
    root = TkinterDnD.Tk()
    app = PixelPruner(root)
    root.mainloop()

if __name__ == "__main__":
    main()
