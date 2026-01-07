"""
Program Deteksi Pelanggar Lalu Lintas
======================================
Mendeteksi pengendara motor yang tidak menggunakan helm
"""

import os
import cv2
from ultralytics import YOLO
from pathlib import Path
import time


def create_output_folders(video_folder, output_base):
    """
    Buat folder output untuk setiap video
    """
    video_files = [f for f in os.listdir(video_folder) if f.endswith(('.mp4', '.avi', '.mov'))]
    output_folders = {}
    
    for video_file in video_files:
        video_name = Path(video_file).stem
        output_path = os.path.join(output_base, video_name)
        os.makedirs(output_path, exist_ok=True)
        output_folders[video_file] = output_path
    
    return output_folders


def process_video(video_path, model, output_folder, fps_limit=10):
    """
    Proses video untuk mendeteksi rider dan crop bounding box
    
    Args:
        video_path: Path ke file video
        model: YOLO model yang sudah di-load
        output_folder: Folder untuk menyimpan hasil crop
        fps_limit: Batasan frame per detik (5-10)
    """
    # Buka video
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"[ERROR] Tidak bisa membuka video: {video_path}")
        return
    
    # Dapatkan FPS asli video
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Hitung frame skip untuk mencapai fps_limit
    frame_skip = max(1, int(original_fps / fps_limit))
    
    print(f"\n[INFO] Memproses: {Path(video_path).name}")
    print(f"[INFO] FPS asli: {original_fps:.2f}, Frame skip: {frame_skip}")
    print(f"[INFO] Total frames: {total_frames}")
    print(f"[INFO] Target FPS: {original_fps / frame_skip:.2f}")
    
    frame_count = 0
    processed_count = 0
    rider_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # Lewati frame sesuai frame_skip
        if frame_count % frame_skip != 0:
            frame_count += 1
            continue
        
        # Jalankan deteksi YOLO
        results = model(frame, verbose=False)
        
        # Proses setiap deteksi
        for result in results:
            boxes = result.boxes
            
            for i, box in enumerate(boxes):
                # Dapatkan class name
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                
                # Hanya proses jika class adalah 'rider'
                if class_name.lower() == 'rider':
                    # Dapatkan koordinat bounding box
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Crop gambar rider
                    cropped_rider = frame[y1:y2, x1:x2]
                    
                    # Generate nama file
                    filename = f"frame_{frame_count:06d}_rider_{rider_count:04d}_conf_{confidence:.2f}.jpg"
                    output_path = os.path.join(output_folder, filename)
                    
                    # Simpan crop
                    cv2.imwrite(output_path, cropped_rider)
                    rider_count += 1
        
        processed_count += 1
        frame_count += 1
        
        # Progress indicator
        if processed_count % 10 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"[INFO] Progress: {progress:.1f}% | Riders detected: {rider_count}", end='\r')
    
    cap.release()
    print(f"\n[INFO] Selesai! Total riders terdeteksi: {rider_count}")
    print(f"[INFO] Hasil disimpan di: {output_folder}\n")


def main():
    """
    Fungsi utama program
    """
    # Konfigurasi path
    model_path = "trained-nano-120epoch-dataset-II.pt"
    video_folder = "tes-video"
    output_base = "output-video"
    
    # FPS limit (5-10 frame per detik)
    fps_limit = 10
    
    # Cek apakah model ada
    if not os.path.exists(model_path):
        print(f"[ERROR] Model tidak ditemukan: {model_path}")
        return
    
    # Cek apakah folder video ada
    if not os.path.exists(video_folder):
        print(f"[ERROR] Folder video tidak ditemukan: {video_folder}")
        return
    
    # Load YOLO model
    print(f"[INFO] Loading YOLO model: {model_path}")
    model = YOLO(model_path)
    print(f"[INFO] Model berhasil di-load!")
    print(f"[INFO] Classes: {model.names}")
    
    # Buat folder output untuk setiap video
    print(f"\n[INFO] Membuat folder output...")
    output_folders = create_output_folders(video_folder, output_base)
    print(f"[INFO] Folder output siap untuk {len(output_folders)} video")
    
    # Proses setiap video
    for video_file, output_folder in output_folders.items():
        video_path = os.path.join(video_folder, video_file)
        process_video(video_path, model, output_folder, fps_limit)
    
    print("\n[INFO] ===== SEMUA VIDEO SELESAI DIPROSES =====")


if __name__ == "__main__":
    main()
