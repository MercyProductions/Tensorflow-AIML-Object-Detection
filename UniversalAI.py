import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import pyautogui
import win32api, win32con, win32gui
import cv2
import math
import time
import logging
import traceback

# ===================== GLOBAL CONFIG VARIABLES ===================== #

WINDOW_TITLE = 'Counter-Strike 2'  # Game window title
SIZE_SCALE = 3  # Scale factor for resizing the screenshot
DETECTION_THRESHOLD = 0.5  # Minimum confidence for detected objects
PERSON_CLASS = 1  # Class ID for 'person'
CLOSEST_DISTANCE_THRESHOLD = 0.45  # Threshold to ignore objects too far vertically
MOUSE_MOVE_SCALE = 1.7  # Scale for adjusting mouse movement
DELAY_BETWEEN_SHOTS = 0.05  # Time between shots
DELAY_BETWEEN_LOOPS = 0.1  # Main loop delay
USE_GPU = True  # Use GPU for TensorFlow if available

# ===================== SETUP LOGGING ===================== #

logging.basicConfig(filename='aimbot.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ===================== TENSORFLOW MODEL LOADING ===================== #

def load_detector():
    logging.info("Loading TensorFlow model...")
    try:
        detector = hub.load("https://tfhub.dev/tensorflow/centernet/resnet50v1_fpn_512x512/1")
        logging.info("Model loaded successfully.")
        return detector
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        raise

detector = load_detector()

# ===================== UTILITY FUNCTIONS ===================== #

def get_window_rect(hwnd):
    try:
        rect = win32gui.GetWindowRect(hwnd)
        logging.info(f"Window rect: {rect}")
        return rect
    except Exception as e:
        logging.error(f"Error getting window rect: {e}")
        return None

def screenshot(region):
    try:
        img = np.array(pyautogui.screenshot(region=region))
        logging.info(f"Screenshot captured: {img.shape}")
        return img
    except Exception as e:
        logging.error(f"Error capturing screenshot: {e}")
        return None

def detect_objects(image):
    try:
        img_w, img_h = image.shape[1], image.shape[0]
        image = np.expand_dims(image, axis=0)
        result = detector(image)
        result = {key: value.numpy() for key, value in result.items()}
        boxes, scores, classes = result['detection_boxes'][0], result['detection_scores'][0], result['detection_classes'][0]
        logging.debug(f"Detection results - boxes: {len(boxes)}, scores: {len(scores)}")
        return boxes, scores, classes, img_w, img_h
    except Exception as e:
        logging.error(f"Error during object detection: {e}")
        return [], [], [], None, None

def process_boxes(boxes, scores, classes, img_w, img_h):
    detected_boxes = []
    for i, box in enumerate(boxes):
        if classes[i] == PERSON_CLASS and scores[i] >= DETECTION_THRESHOLD:
            ymin, xmin, ymax, xmax = box
            if ymin > 0.5 and ymax > CLOSEST_DISTANCE_THRESHOLD:
                continue
            left, right, top, bottom = int(xmin * img_w), int(xmax * img_w), int(ymin * img_h), int(ymax * img_h)
            detected_boxes.append((left, right, top, bottom))
    logging.info(f"Detected {len(detected_boxes)} valid boxes.")
    return detected_boxes

def find_closest_box(detected_boxes, img_w, img_h):
    min_dist = float('inf')
    closest_index = -1
    centers = []
    for i, box in enumerate(detected_boxes):
        x1, x2, y1, y2 = box
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        centers.append((center_x, center_y))
        dist = math.sqrt(math.pow(img_w / 2 - center_x, 2) + math.pow(img_h / 2 - center_y, 2))
        if dist < min_dist:
            min_dist = dist
            closest_index = i
    logging.debug(f"Closest box index: {closest_index}, distance: {min_dist}")
    return closest_index, centers

def aim_and_shoot(closest_center, detected_box, img_w, img_h):
    try:
        if closest_center:
            x_diff = closest_center[0] - img_w / 2
            y_diff = closest_center[1] - img_h / 2 - (detected_box[3] - detected_box[2]) * CLOSEST_DISTANCE_THRESHOLD
            x_movement = int(x_diff * MOUSE_MOVE_SCALE * SIZE_SCALE)
            y_movement = int(y_diff * MOUSE_MOVE_SCALE * SIZE_SCALE)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x_movement, y_movement, 0, 0)
            time.sleep(DELAY_BETWEEN_SHOTS)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            logging.info(f"Aimed and shot at position: {x_movement}, {y_movement}")
    except Exception as e:
        logging.error(f"Error during aiming/shooting: {e}")

# ===================== MAIN FUNCTION ===================== #

def main():
    while True:
        try:
            hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
            rect = get_window_rect(hwnd)
            if rect:
                region = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                ori_img = screenshot(region)
                if ori_img is not None:
                    ori_img = cv2.resize(ori_img, (ori_img.shape[1] // SIZE_SCALE, ori_img.shape[0] // SIZE_SCALE))
                    boxes, scores, classes, img_w, img_h = detect_objects(ori_img)
                    detected_boxes = process_boxes(boxes, scores, classes, img_w, img_h)

                    if detected_boxes:
                        closest_index, centers = find_closest_box(detected_boxes, img_w, img_h)
                        if closest_index != -1:
                            aim_and_shoot(centers[closest_index], detected_boxes[closest_index], img_w, img_h)

            time.sleep(DELAY_BETWEEN_LOOPS)
        except Exception as e:
            logging.error(f"Fatal error in main loop: {e}")
            logging.error(traceback.format_exc())
            time.sleep(1)

if __name__ == "__main__":
    main()
