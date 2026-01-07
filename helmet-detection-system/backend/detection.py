import cv2
import numpy as np
from ultralytics import YOLO
from paddleocr import PaddleOCR
import os
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import torch

class Detector:
    def __init__(self, yolo_weights_path='yolov11x.pt'):
        # Check CUDA
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[INFO] Using Device: {self.device}")
        
        path_to_check = r"../../trained-nano-120epoch-dataset-II.pt"
        if os.path.exists(path_to_check):
             print(f"[INFO] Loading Custom YOLO: {path_to_check}")
             self.yolo_model = YOLO(path_to_check)
        else:
             print("[WARNING] Custom weights not found, using default yolov8n.pt")
             self.yolo_model = YOLO("yolov8n.pt") 
        
        # Move to device explicitly if needed, usually ultralytics handles it but being explicit helps debug
        self.yolo_model.to(self.device)

        # PaddleOCR (gpu=True if cuda available)
        use_gpu = (self.device == 'cuda')
        print(f"[INFO] Initializing PaddleOCR (use_gpu={use_gpu})...")
        # Removing use_gpu and show_log args as they are causing ValueError in this version
        self.ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
        self.frame_count = 0
        
        # Async OCR
        self.ocr_executor = ThreadPoolExecutor(max_workers=1)
        
        # Ensure crops directory exists
        self.crops_dir = os.path.join(os.getcwd(), 'static', 'crops')
        os.makedirs(self.crops_dir, exist_ok=True)
        
        self.logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file = os.path.join(self.logs_dir, 'detections.json')
        
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)
        
        # FPS calculation
        self.prev_time = 0
        
        # Track recent detections to avoid redundancy: list of (center_x, center_y, timestamp)
        self.recent_detections = []

    def extract_license_plate(self, image, bbox):
        x1, y1, x2, y2 = map(int, bbox)
        height, width = image.shape[:2]
        pad = 5
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(width, x2 + pad)
        y2 = min(height, y2 + pad)
        return image[y1:y2, x1:x2]

    # ... Include other helper functions from detect_and_ocr.py ...
    # (Retaining previous helper methods: order_points, perspective_transform, deskew_image, preprocess_plate_image)
    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def perspective_transform(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return image
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2).astype("float32")
                rect = self.order_points(pts)
                (tl, tr, br, bl) = rect
                widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                maxWidth = max(int(widthA), int(widthB))
                heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                maxHeight = max(int(heightA), int(heightB))
                if maxWidth < 50 or maxHeight < 20: continue
                aspect_ratio = maxWidth / maxHeight
                if not (1.5 < aspect_ratio < 6.0): continue
                dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
                return warped
        return image

    def deskew_image(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 10: return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45: angle = 90 + angle
        elif angle > 45: angle = angle - 90
        if abs(angle) < 0.5: return image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def preprocess_plate_image(self, plate_img):
        if plate_img is None or plate_img.size == 0: return plate_img
        height, width = plate_img.shape[:2]
        if width < 200:
            scale = 200 / width
            plate_img = cv2.resize(plate_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        plate_img = self.perspective_transform(plate_img)
        plate_img = self.deskew_image(plate_img)
        denoised = cv2.bilateralFilter(plate_img, 9, 75, 75)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        kernel = np.array([[-1, -1, -1], [-1,  9, -1], [-1, -1, -1]])
        result = cv2.filter2D(result, -1, kernel)
        return result

    def perform_ocr(self, plate_img):
        try:
            result = self.ocr_model.predict(plate_img)
            if result is None: return "", 0.0
            texts = []
            confidences = []
            
            # Robust result parsing matching detect_and_ocr.py
            for item in result:
                if hasattr(item, 'rec_texts') and hasattr(item, 'rec_scores'):
                    # PaddleOCR v3.x object format
                    for text, score in zip(item.rec_texts, item.rec_scores):
                        if text and score > 0:
                            texts.append(text)
                            confidences.append(float(score))
                elif isinstance(item, dict):
                    # Dictionary format
                    if 'rec_texts' in item and 'rec_scores' in item:
                        for text, score in zip(item['rec_texts'], item['rec_scores']):
                            if text and score > 0:
                                texts.append(text)
                                confidences.append(float(score))
                elif isinstance(item, (list, tuple)):
                    # Legacy list format
                    for detection in item if item else []:
                        if detection and len(detection) >= 2:
                            text_info = detection[1]
                            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                texts.append(str(text_info[0]))
                                confidences.append(float(text_info[1]))
                            elif isinstance(text_info, str):
                                texts.append(text_info)
                                confidences.append(0.5)

            if texts:
                return " ".join(texts), sum(confidences)/len(confidences)
            return "", 0.0
        except Exception as e:
            print(f"[OCR ERROR] {e}")
            return "", 0.0

    def compute_iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        return inter_area / float(box1_area + box2_area - inter_area)
        
    def is_inside(self, inner_box, outer_box):
        cx = (inner_box[0] + inner_box[2]) / 2
        cy = (inner_box[1] + inner_box[3]) / 2
        return (outer_box[0] <= cx <= outer_box[2] and 
                outer_box[1] <= cy <= outer_box[3])
    
    def is_duplicate_request(self, center, threshold_dist=50, threshold_time=3.0):
        current_time = time.time()
        # Filter old detections
        self.recent_detections = [d for d in self.recent_detections if current_time - d[2] < threshold_time]
        
        # Check distance
        cx, cy = center
        for (rcx, rcy, rtime) in self.recent_detections:
            dist = np.sqrt((cx - rcx)**2 + (cy - rcy)**2)
            if dist < threshold_dist:
                return True
        
        # Add new
        self.recent_detections.append((cx, cy, current_time))
        return False
    
    def async_process_plate(self, plate_img_copy, bbox):
        """Background task for OCR"""
        try:
            # Preprocess
            text, conf = self.perform_ocr(plate_img_copy)
            
            if conf < 0.7:
                 pp_img = self.preprocess_plate_image(plate_img_copy)
                 text2, conf2 = self.perform_ocr(pp_img)
                 if conf2 > conf:
                     text, conf = text2, conf2

            print(text, conf)

            if text:
                print(f"[OCR SUCCESS] {text} ({conf:.2f})")
                filename = f"violation_{int(time.time())}_{self.frame_count}.jpg"
                filepath = os.path.join(self.crops_dir, filename)
                cv2.imwrite(filepath, plate_img_copy)
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "plate_text": text,
                    "confidence": float(conf),
                    "image_path": f"/static/crops/{filename}",
                    "type": "No Helmet"
                }
                self.save_logs([log_entry])
            else:
                # Save failed crop for debugging
                filename = f"failed_ocr_{int(time.time())}_{self.frame_count}.jpg"
                filepath = os.path.join(self.crops_dir, filename)
                cv2.imwrite(filepath, plate_img_copy)
                print(f"[OCR FAIL] Ditemukan plat tapi teks tidak terbaca. Saved to {filename}")
        except Exception as e:
            print(f"[ASYNC ERROR] {e}")

    def detect(self, frame):
        # FPS Calculation
        curr_time = time.time()
        fps = 1 / (curr_time - self.prev_time) if self.prev_time > 0 else 0
        self.prev_time = curr_time
        
        self.frame_count += 1
        
        # YOLO Detection
        results = self.yolo_model(frame, verbose=False)
        annotated_frame = frame.copy()
        
        detections = {'with helmet': [], 'without helmet': [], 'rider': [], 'number plate': []}
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())
                name = self.yolo_model.names[cls]
                
                det = {'bbox': [x1, y1, x2, y2], 'conf': conf}
                if name in detections:
                    detections[name].append(det)
                
                # Draw
                color = (0, 255, 0)
                if name == 'without helmet': color = (0, 0, 255)
                if name == 'rider': color = (255, 0, 0)
                if name == 'number plate': color = (255, 255, 0)
                
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(annotated_frame, f"{name} {conf:.2f}", (int(x1), int(y1)-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Logic: No Helmet -> Rider -> Plate -> OCR
        should_ocr = (self.frame_count % 10 == 0)

        for no_helmet in detections['without helmet']:
            associated_rider = None
            best_iou = 0
            
            for rider in detections['rider']:
                if self.is_inside(no_helmet['bbox'], rider['bbox']):
                    associated_rider = rider
                    break 
                iou = self.compute_iou(no_helmet['bbox'], rider['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    associated_rider = rider
            
            if associated_rider:
                # Draw line
                cv2.line(annotated_frame, 
                         (int(no_helmet['bbox'][0]), int(no_helmet['bbox'][1])), 
                         (int(associated_rider['bbox'][0]), int(associated_rider['bbox'][1])), 
                         (0, 0, 255), 2)
                
                associated_plate = None
                for plate in detections['number plate']:
                     if self.is_inside(plate['bbox'], associated_rider['bbox']):
                         associated_plate = plate
                         break
                
                if associated_plate:
                     # Center of plate
                     px = (associated_plate['bbox'][0] + associated_plate['bbox'][2]) / 2
                     py = (associated_plate['bbox'][1] + associated_plate['bbox'][3]) / 2
                     
                     # Draw "Plate Detected" indicator
                     cv2.putText(annotated_frame, "Plate Detected", 
                                (int(associated_plate['bbox'][0]), int(associated_plate['bbox'][1])-20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                     if should_ocr:
                        # Check spatial redundancy
                        if not self.is_duplicate_request((px, py)):
                            # Offload to thread
                            plate_img = self.extract_license_plate(frame, associated_plate['bbox'])
                            # Must copy image for thread safety as 'frame' changes
                            plate_img_copy = plate_img.copy() 
                            self.ocr_executor.submit(self.async_process_plate, plate_img_copy, associated_plate['bbox'])
                            
                            cv2.putText(annotated_frame, "OCR Processing...", 
                                    (int(associated_plate['bbox'][0]), int(associated_plate['bbox'][1])-35),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                        else:
                            # It is duplicate
                             cv2.putText(annotated_frame, "OCR Skipped (Recent)", 
                                    (int(associated_plate['bbox'][0]), int(associated_plate['bbox'][1])-35),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 2)

        # Draw FPS
        cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return annotated_frame

    def save_logs(self, new_logs):
        try:
            # Simple read-modify-write (assuming low concurrency for file access)
            # In production, use database or robust locking
            if not os.path.exists(self.log_file):
                 data = []
            else:
                 with open(self.log_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except:
                        data = []
            
            data.extend(new_logs)
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[LOG ERROR] {e}")

