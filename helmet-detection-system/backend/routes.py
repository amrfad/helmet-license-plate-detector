from flask import Blueprint, Response, request, jsonify, current_app
from camera import VideoCamera
from detection import Detector
import cv2
import threading
import time
import json
import os

api = Blueprint('api', __name__)

# Global state
camera = None
detector = None
lock = threading.Lock()

def get_camera():
    global camera
    if camera is None:
        camera = VideoCamera(0) # Default to webcam
    return camera

def get_detector():
    global detector
    if detector is None:
        detector = Detector()
    return detector

def gen_frames():
    cam = get_camera()
    det = get_detector()
    
    while True:
        frame = cam.get_frame()
        if frame is not None:
            # Run detection
            annotated_frame = det.detect(frame)
            
            # Encode
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            time.sleep(0.1)

@api.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@api.route('/api/config', methods=['POST'])
def config():
    global camera
    data = request.json
    mode = data.get('mode') # 'webcam', 'file', 'rtsp'
    value = data.get('value') # path or url
    
    source = 0
    if mode == 'webcam':
        try:
            source = int(value) if value else 0
        except:
            source = 0
    elif mode == 'file':
        if not os.path.exists(value):
            return jsonify({"status": "error", "message": "File not found"}), 400
        source = value
    elif mode == 'rtsp':
        source = value
        
    with lock:
        if camera:
            camera.set_source(source)
        else:
            camera = VideoCamera(source)
            
    return jsonify({"status": "ok", "mode": mode, "source": source})

@api.route('/api/logs', methods=['GET'])
def get_logs():
    log_file = os.path.join(current_app.root_path, 'logs', 'detections.json')
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            try:
                data = json.load(f)
                return jsonify(data)
            except:
                return jsonify([])
    return jsonify([])

@api.route('/api/status', methods=['GET'])
def status():
    # Return verification that backend is running
    return jsonify({"status": "running"})
