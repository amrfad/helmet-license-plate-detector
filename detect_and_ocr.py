"""
Program Deteksi Objek YOLOv11 + PaddleOCR
=========================================
Mendeteksi: with helmet, without helmet, rider, number plate
Mengekstrak number plate dan membaca teks dengan PaddleOCR
"""

import os
import cv2
import numpy as np
from ultralytics import YOLO
from paddleocr import PaddleOCR
from pathlib import Path


def load_models(yolo_weights_path):
    """
    Load YOLO dan PaddleOCR models
    """
    # Load YOLO model
    print(f"[INFO] Loading YOLO model dari: {yolo_weights_path}")
    yolo_model = YOLO(yolo_weights_path)
    
    # Load PaddleOCR
    print("[INFO] Loading PaddleOCR model...")
    ocr_model = PaddleOCR(
        use_angle_cls=True,
        lang='en'  # Bahasa Inggris untuk plat nomor
    )
    
    return yolo_model, ocr_model


def extract_license_plate(image, bbox):
    """
    Ekstrak region license plate dari gambar
    
    Args:
        image: Gambar asli (numpy array)
        bbox: Bounding box [x1, y1, x2, y2]
    
    Returns:
        Cropped image dari license plate
    """
    x1, y1, x2, y2 = map(int, bbox)
    
    # Tambah sedikit padding untuk hasil OCR yang lebih baik
    height, width = image.shape[:2]
    pad = 5
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(width, x2 + pad)
    y2 = min(height, y2 + pad)
    
    cropped = image[y1:y2, x1:x2]
    return cropped


def order_points(pts):
    """
    Urutkan 4 titik sudut: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    # Top-left akan memiliki sum terkecil
    # Bottom-right akan memiliki sum terbesar
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Top-right akan memiliki diff terkecil
    # Bottom-left akan memiliki diff terbesar
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect


def perspective_transform(image):
    """
    Deteksi dan koreksi perspektif plat nomor
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Blur untuk mengurangi noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Dilasi untuk menghubungkan edge yang terputus
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)
    
    # Cari kontur
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image
    
    # Cari kontur terbesar yang menyerupai persegi panjang
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        # Jika kontur memiliki 4 titik, kemungkinan itu plat
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
            rect = order_points(pts)
            
            # Hitung dimensi output
            (tl, tr, br, bl) = rect
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            
            # Skip jika dimensi tidak valid atau rasio tidak seperti plat nomor
            if maxWidth < 50 or maxHeight < 20:
                continue
            
            aspect_ratio = maxWidth / maxHeight
            if not (1.5 < aspect_ratio < 6.0):  # Rasio plat nomor biasanya 2:1 hingga 5:1
                continue
            
            # Perspective transform
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
            
            return warped
    
    return image


def deskew_image(image):
    """
    Koreksi kemiringan (skew) pada gambar
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Threshold untuk mendapatkan teks
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Cari koordinat pixel non-zero
    coords = np.column_stack(np.where(thresh > 0))
    
    if len(coords) < 10:
        return image
    
    # Hitung sudut kemiringan dengan minAreaRect
    angle = cv2.minAreaRect(coords)[-1]
    
    # Koreksi sudut
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    
    # Jika sudut kecil, tidak perlu koreksi
    if abs(angle) < 0.5:
        return image
    
    # Rotasi gambar
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), 
                              flags=cv2.INTER_CUBIC, 
                              borderMode=cv2.BORDER_REPLICATE)
    
    return rotated


def preprocess_plate_image(plate_img):
    """
    Preprocessing gambar plat nomor untuk OCR yang lebih baik
    """
    if plate_img is None or plate_img.size == 0:
        return plate_img
    
    # 1. Resize jika terlalu kecil
    height, width = plate_img.shape[:2]
    if width < 200:
        scale = 200 / width
        plate_img = cv2.resize(plate_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # 2. Perspective transform (koreksi sudut pandang)
    plate_img = perspective_transform(plate_img)
    
    # 3. Deskew (koreksi kemiringan)
    plate_img = deskew_image(plate_img)
    
    # 4. Denoise dengan bilateral filter (preservasi edge)
    denoised = cv2.bilateralFilter(plate_img, 9, 75, 75)
    
    # 5. Tingkatkan kontras dengan CLAHE
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    # 6. Sharpening
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    result = cv2.filter2D(result, -1, kernel)
    
    return result


def perform_ocr(ocr_model, plate_img):
    """
    Melakukan OCR pada gambar plat nomor
    
    Args:
        ocr_model: PaddleOCR model
        plate_img: Gambar plat nomor (numpy array)
    
    Returns:
        Tuple (text, confidence)
    """
    try:
        # OCR pada gambar menggunakan predict (PaddleOCR v3.x)
        result = ocr_model.predict(plate_img)
        
        if result is None:
            return "", 0.0
        
        # Gabungkan semua teks yang terdeteksi
        texts = []
        confidences = []
        
        # Handle hasil dari PaddleOCR v3.x
        for item in result:
            if hasattr(item, 'rec_texts') and hasattr(item, 'rec_scores'):
                # Format baru PaddleOCR v3.x
                for text, score in zip(item.rec_texts, item.rec_scores):
                    if text and score > 0:
                        texts.append(text)
                        confidences.append(float(score))
            elif isinstance(item, dict):
                # Format dictionary
                if 'rec_texts' in item and 'rec_scores' in item:
                    for text, score in zip(item['rec_texts'], item['rec_scores']):
                        if text and score > 0:
                            texts.append(text)
                            confidences.append(float(score))
            elif isinstance(item, (list, tuple)):
                # Format lama - list of detections
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
            combined_text = " ".join(texts)
            avg_conf = sum(confidences) / len(confidences)
            return combined_text, avg_conf
        
        return "", 0.0
        
    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return "", 0.0


def detect_and_recognize(image_path, yolo_model, ocr_model, conf_threshold=0.25):
    """
    Deteksi objek dan recognition plat nomor
    
    Args:
        image_path: Path ke gambar
        yolo_model: YOLO model
        ocr_model: PaddleOCR model
        conf_threshold: Confidence threshold untuk deteksi
    
    Returns:
        Tuple (annotated_image, detections_dict)
    """
    # Baca gambar
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"[ERROR] Tidak dapat membaca gambar: {image_path}")
        return None, None
    
    # Deteksi dengan YOLO
    results = yolo_model(image, conf=conf_threshold, verbose=False)
    
    # Dictionary untuk menyimpan hasil
    detections = {
        'with helmet': [],
        'without helmet': [],
        'rider': [],
        'number plate': []
    }
    
    # Class names dari model
    class_names = yolo_model.names
    
    # Annotated image
    annotated = image.copy()
    
    # Warna untuk setiap class
    colors = {
        'with helmet': (0, 255, 0),       # Hijau
        'without helmet': (0, 165, 255),  # Orange
        'rider': (255, 0, 0),             # Biru
        'number plate': (0, 0, 255)       # Merah
    }
    
    plate_count = 0
    
    for result in results:
        boxes = result.boxes
        
        for box in boxes:
            # Ambil informasi box
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            class_name = class_names[cls_id]
            
            # Simpan deteksi
            detection_info = {
                'bbox': [x1, y1, x2, y2],
                'confidence': conf
            }
            
            if class_name in detections:
                # Jika number plate, lakukan OCR
                if class_name == 'number plate':
                    plate_count += 1
                    
                    # Ekstrak plat nomor
                    plate_img = extract_license_plate(image, [x1, y1, x2, y2])
                    
                    # OCR pada gambar asli
                    text, ocr_conf = perform_ocr(ocr_model, plate_img)
                    
                    # Jika hasil kurang baik, coba dengan preprocessing
                    if ocr_conf < 0.7:
                        preprocessed = preprocess_plate_image(plate_img)
                        text2, ocr_conf2 = perform_ocr(ocr_model, preprocessed)
                        if ocr_conf2 > ocr_conf:
                            text, ocr_conf = text2, ocr_conf2
                    
                    detection_info['ocr_text'] = text
                    detection_info['ocr_confidence'] = ocr_conf
                    
                    print(f"[PLATE {plate_count}] Detected: '{text}' (conf: {ocr_conf:.2f})")
                
                detections[class_name].append(detection_info)
            
            # Draw bounding box
            color = colors.get(class_name, (255, 255, 255))
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # Label
            label = f"{class_name}: {conf:.2f}"
            if class_name == 'number plate' and 'ocr_text' in detection_info:
                label += f" [{detection_info['ocr_text']}]"
            
            # Background untuk label
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (int(x1), int(y1) - label_h - 10), 
                         (int(x1) + label_w, int(y1)), color, -1)
            cv2.putText(annotated, label, (int(x1), int(y1) - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return annotated, detections


def process_directory(input_dir, yolo_model, ocr_model, output_dir="output"):
    """
    Proses semua gambar dalam direktori
    """
    # Buat output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Supported extensions
    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
    
    # Cari semua gambar (case-insensitive, tanpa duplikat)
    image_paths = []
    seen = set()
    for ext in extensions:
        for p in Path(input_dir).glob(f"*{ext}"):
            if p.name.lower() not in seen:
                seen.add(p.name.lower())
                image_paths.append(p)
        for p in Path(input_dir).glob(f"*{ext.upper()}"):
            if p.name.lower() not in seen:
                seen.add(p.name.lower())
                image_paths.append(p)
    
    if not image_paths:
        print(f"[WARNING] Tidak ada gambar ditemukan di: {input_dir}")
        return
    
    print(f"\n[INFO] Ditemukan {len(image_paths)} gambar untuk diproses\n")
    print("=" * 60)
    
    all_results = {}
    
    for idx, img_path in enumerate(image_paths, 1):
        print(f"\n[{idx}/{len(image_paths)}] Processing: {img_path.name}")
        print("-" * 40)
        
        # Deteksi dan OCR
        annotated, detections = detect_and_recognize(img_path, yolo_model, ocr_model)
        
        if annotated is not None:
            # Simpan hasil
            output_path = os.path.join(output_dir, f"result_{img_path.name}")
            cv2.imwrite(output_path, annotated)
            print(f"[SAVED] Hasil disimpan ke: {output_path}")
            
            # Ringkasan deteksi
            print(f"\n[SUMMARY]")
            print(f"  - With Helmet: {len(detections['with helmet'])} terdeteksi")
            print(f"  - Without Helmet: {len(detections['without helmet'])} terdeteksi")
            print(f"  - Rider: {len(detections['rider'])} terdeteksi")
            print(f"  - Number Plate: {len(detections['number plate'])} terdeteksi")
            
            # Detail plat nomor
            for i, plate in enumerate(detections['number plate'], 1):
                print(f"\n  [Number Plate {i}]")
                print(f"    OCR Text: {plate.get('ocr_text', 'N/A')}")
                print(f"    OCR Confidence: {plate.get('ocr_confidence', 0):.2%}")
            
            all_results[str(img_path)] = detections
    
    print("\n" + "=" * 60)
    print("[DONE] Semua gambar telah diproses!")
    
    return all_results


def main():
    # Konfigurasi path
    YOLO_WEIGHTS = "trained-small-40epoch-dataset-II.pt"
    TEST_IMAGES_DIR = "tes-gambar"
    OUTPUT_DIR = "output"
    
    # Verifikasi file exists
    if not os.path.exists(YOLO_WEIGHTS):
        print(f"[ERROR] File weights tidak ditemukan: {YOLO_WEIGHTS}")
        return
    
    if not os.path.exists(TEST_IMAGES_DIR):
        print(f"[ERROR] Direktori gambar tidak ditemukan: {TEST_IMAGES_DIR}")
        return
    
    # Load models
    yolo_model, ocr_model = load_models(YOLO_WEIGHTS)
    
    # Print class names
    print(f"\n[INFO] Class yang terdeteksi: {yolo_model.names}")
    
    # Proses gambar
    results = process_directory(TEST_IMAGES_DIR, yolo_model, ocr_model, OUTPUT_DIR)
    
    return results


if __name__ == "__main__":
    main()
