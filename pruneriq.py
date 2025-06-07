import os
import json
from PIL import Image
import cv2
import numpy as np

def analyze_image(image_path):
    image = cv2.imread(image_path)

    # Contrast: Standard deviation of intensity
    contrast = float(np.std(image))

    # Clarity: Variance of Laplacian
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clarity = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Noise: Estimate via FFT residuals or pixel variance
    noise = float(np.var(cv2.GaussianBlur(gray, (3,3), 0) - gray))

    # Placeholder: Aesthetic score stub
    aesthetic = 0.0  # Will replace with actual model output later

    return {
        "filename": os.path.basename(image_path),
        "contrast": contrast,
        "clarity": clarity,
        "noise": noise,
        "aesthetic": aesthetic
    }

def analyze_folder(folder_path):
    results = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image_path = os.path.join(folder_path, file)
            result = analyze_image(image_path)
            results.append(result)
    return results
