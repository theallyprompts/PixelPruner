# PixelPruner
PixelPruner is a user-friendly image cropping app for AI-generated art. It supports PNG, JPG, JPEG, and WEBP formats. Easily crop, preview, and manage images with interactive previews, thumbnail views, rotation tools, and customizable output folders. Streamline your workflow and achieve perfect crops every time with PixelPruner.

![image](https://github.com/theallyprompts/PixelPruner/assets/133992794/2de5d40b-c417-4779-a429-cdabd575c307)

![image](https://github.com/theallyprompts/PixelPruner/assets/133992794/685915de-e7f3-4946-95e4-682420d68d2a)



# Features
- **Multi-Format Support**: Supports cropping images in PNG, JPG, JPEG, and WEBP formats. Crops are converted to PNG.

- **Interactive Crop Previews**: Preview your crop selection in real-time with an interactive preview pane, before you make the crop.

 ![image](https://github.com/theallyprompts/PixelPruner/assets/133992794/5768c2f2-7573-4700-a79d-b38508ac9307)

- **Thumbnail View of Crops**: View all your cropped images as thumbnails in a dedicated pane, making it easy to manage and review your work.

  ![image](https://github.com/theallyprompts/PixelPruner/assets/133992794/d64c84f0-7e96-4a10-b15e-431f8be3f6e7)

- **Rotation Tools**: Easily rotate images to achieve the perfect orientation before cropping.

  ![image](https://github.com/theallyprompts/PixelPruner/assets/133992794/9049de14-ca20-4151-ac61-b473b5edd2c2)

- **Multi-Crops**: Make multiple crops from the same image. Multiple faces? No problem!

- **Customizable Output Folder**: Choose a custom folder to save your cropped images.

- **Zip Crops**: Quickly zip all cropped images into a single archive for easy sharing, storage, or upload to the Civitai.com on-site LoRA Trainer

  ![image](https://github.com/theallyprompts/PixelPruner/assets/133992794/71477f5b-7447-43cc-b996-bdb9a17dea2d)

- **Undo Crop Actions**: Made a mistake? Simply undo the last crop with the click of a button.

- **Keyboard Shortcuts**: Navigate and manipulate images effortlessly with convenient WASD keyboard shortcuts.

  ---

## Installation Guide - Prebuilt App

Head to the **[Releases](https://github.com/theallyprompts/PixelPruner/releases/tag/v1.0.0)** and download the latest .exe version - pre-packaged with Python and ready to run (no installation required!)

---

## Installation Guide - Manual Install

Follow these steps to install and run PixelPruner on your local machine.

### Prerequisites

1. **Python 3.x**: Make sure you have Python 3.x installed on your system. You can download it from the [official Python website](https://www.python.org/downloads/).

2. **Pillow**: This library is required for image processing. You can install it with the `pip` package manager.

### Step-by-Step Installation

1. **Clone the Repository**

   Clone the PixelPruner repository from GitHub to your local machine using the following command:

   ```sh
   git clone https://github.com/theallyprompts/PixelPruner.git
   ```

2. **Navigate to the cloned directory**

3. **Set Up a Virtual Environment (Optional but Recommended)**

   It is recommended to use a virtual environment to manage dependencies. Create and activate a virtual environment:

   ```sh
   python -m venv venv
   source venv/bin/activate   # On Windows use `venv\Scripts\activate`
   ```

4. **Install Dependencies**

    Install the required dependencies using pip:

    ```sh
    pip install pillow[webp]
    ```

    If you're on Linux, you might need to install tkinter separately:

    ```sh
    sudo apt-get install python3-tk
    ```

5. **Running the Application**

    Run the PixelPruner application using the following command: 

    ```sh
    python PixelPruner.py
    ```

---

### Using PixelPruner

**Select Folder**: Upon launching the application, you will be prompted to select a folder containing the images you want to crop.

**Select Crop Dimensions**: From the dropdown in the top left, select the output dimensions for your crops.

**Set an output Directory** (optional): Click the **Set Output Folder** button to pick an output directory. If no directory is chosen, PixelPruner will place crops beside the original images.

**Crop and Manage Images**: Use the interactive tools to crop, rotate, and manage your images. Cropped images can be previewed and saved to a custom output folder.

**Keyboard Shortcuts**: Use keyboard shortcuts (W, S) to navigate through images and (A, D) to rotate them.

---

### Created By...

**[TheAlly](https://civitai.com/user/theally)** - A coding amateur with zero application development experience - just enough to be dangerous. I threw this together with the help of **ChatGPT 4o** because I couldn't find a tool which offered the features I required in a cropping/data set prep tool for LoRA Training.
