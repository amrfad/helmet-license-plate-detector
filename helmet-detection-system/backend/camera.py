import cv2
import threading
import time

class VideoCamera:
    def __init__(self, source=0):
        """
        source: 
          - int for webcam index (e.g. 0)
          - str for file path or RTSP url
        """
        self.source = source
        self.lock = threading.Lock()
        self.video = None
        self._open_video()

    def _open_video(self):
        if self.video is not None and self.video.isOpened():
            self.video.release()
        
        print(f"[INFO] Opening video source: {self.source}")
        
        # On Windows, cv2.CAP_DSHOW is often required for webcams
        if isinstance(self.source, int):
            self.video = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        else:
            self.video = cv2.VideoCapture(self.source)

        if not self.video.isOpened():
            print(f"[ERROR] Could not open video source: {self.source}")
        else:
            print(f"[INFO] Video source opened successfully: {self.source}")

    def __del__(self):
        if self.video and self.video.isOpened():
            self.video.release()

    def get_frame(self):
        with self.lock:
            if self.video is None or not self.video.isOpened():
                return None
            
            success, frame = self.video.read()
            if not success:
                if isinstance(self.source, int):
                     print(f"[WARNING] Failed to read frame from webcam {self.source}")
                
                # If it's a file, loop it.  
                # Check string type safely
                if isinstance(self.source, str) and not self.source.startswith('rtsp'):
                     self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                     success, frame = self.video.read()
                     if not success: 
                         return None
                else:
                    return None
            
            return frame

    def set_source(self, new_source):
        with self.lock:
            if self.source == new_source:
                 return
            self.source = new_source
            self._open_video()
