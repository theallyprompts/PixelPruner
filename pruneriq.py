"""Utility functions for analysing cropped images.

Metrics explained
-----------------
``contrast``
    Standard deviation of all pixel intensities. Higher values indicate
    greater difference between dark and light areas.
``clarity``
    Variance of the Laplacian of the greyscale image. This acts as a
    measure of sharpness where larger numbers mean more defined edges.
``noise``
    Estimate of noise based on the variance between the original
    greyscale image and a blurred version. Lower values are better.
``aesthetic``
    Placeholder score for a future aesthetic model.

Each image is also given a simple rating (``Poor`` through ``Excellent``)
derived from threshold values of the above metrics.  In addition to the
raw values, each metric is converted to a 0-100 ``*_pct`` score using the
thresholds as reference points.  These scores provide an easy-to-read
percentage indicating how close a metric is to the desired range.  The
``reason`` field in the returned dictionary briefly explains why a
particular rating was chosen.
"""

import os
import json
from PIL import Image
import cv2
import numpy as np

# Empirically tuned thresholds for a "good" image
# Typical high‑quality crops have a contrast standard deviation
# around 60–80 on the 0‑255 intensity scale.
CONTRAST_THRESHOLD = 70

# Laplacian variance for sharp images can easily exceed 200.
CLARITY_THRESHOLD = 200

# Noise variance from the blur residual often reaches the
# thousands. Values under about 15000 typically correspond to
# images that look relatively clean while larger values show
# obvious grain.
NOISE_THRESHOLD = 15000

def _scale_score(value: float, threshold: float, reverse: bool = False) -> float:
    """Return a 0-100 score relative to the given threshold."""
    ratio = value / threshold
    ratio = max(0.0, min(ratio, 1.0))
    score = (1.0 - ratio) if reverse else ratio
    return score * 100

def _rate_image(contrast: float, clarity: float, noise: float):
    """Return a textual rating and explanation for the given metrics."""
    score = 0
    reasons = []
    if contrast >= CONTRAST_THRESHOLD:
        score += 1
    else:
        reasons.append("low contrast")
    if clarity >= CLARITY_THRESHOLD:
        score += 1
    else:
        reasons.append("low clarity")
    if noise <= NOISE_THRESHOLD:
        score += 1
    else:
        reasons.append("high noise")

    rating_map = {3: "Excellent", 2: "Good", 1: "Fair", 0: "Poor"}
    rating = rating_map[score]
    if not reasons:
        reasons.append("meets all thresholds")
    return rating, ", ".join(reasons)

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

    contrast_pct = _scale_score(contrast, CONTRAST_THRESHOLD)
    clarity_pct = _scale_score(clarity, CLARITY_THRESHOLD)
    noise_pct = _scale_score(noise, NOISE_THRESHOLD, reverse=True)

    rating, reason = _rate_image(contrast, clarity, noise)

    return {
        "filename": os.path.basename(image_path),
        "contrast": contrast,
        "contrast_pct": contrast_pct,
        "clarity": clarity,
        "clarity_pct": clarity_pct,
        "noise": noise,
        "noise_pct": noise_pct,
        "aesthetic": aesthetic,
        "rating": rating,
        "reason": reason
    }

def analyze_folder(folder_path, crops_only=True, progress_callback=None):
    """Analyze images in ``folder_path``.

    Parameters
    ----------
    folder_path : str
        Directory containing images to analyze.
    crops_only : bool, optional
        If ``True`` only files whose names start with ``"cropped_"`` will be
        processed.  When ``False`` all supported image files are analyzed.

    progress_callback : callable, optional
        Function called with the current index and total count after each image
        is processed.  This can be used to update a progress indicator.

    Returns
    -------
    list[dict]
        A list of metric dictionaries for each image.
    """

    results = []
    files = [
        f
        for f in os.listdir(folder_path)
        if (not crops_only or f.lower().startswith("cropped_"))
        and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    total = len(files)
    for idx, file in enumerate(files, 1):
        image_path = os.path.join(folder_path, file)
        result = analyze_image(image_path)
        results.append(result)
        if progress_callback:
            progress_callback(idx, total)
    return results
