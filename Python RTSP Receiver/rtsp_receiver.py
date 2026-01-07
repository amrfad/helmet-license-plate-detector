import cv2

# URL RTSP
rtsp_url = "rtsp://192.168.68.139:8554/mjpeg/1"

# Buka koneksi ke stream RTSP
cap = cv2.VideoCapture(rtsp_url)

# Periksa apakah koneksi berhasil
if not cap.isOpened():
    print("Error: Tidak dapat membuka stream RTSP")
    exit()

print("Stream RTSP berhasil dibuka. Tekan 'q' untuk keluar.")

# Loop untuk membaca dan menampilkan frame
while True:
    # Baca frame dari stream
    ret, frame = cap.read()
    
    # Jika frame tidak berhasil dibaca, keluar dari loop
    if not ret:
        print("Error: Tidak dapat membaca frame dari stream")
        break
    
    # Tampilkan frame
    cv2.imshow('RTSP Stream', frame)
    
    # Tekan 'q' untuk keluar
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Lepaskan resource
cap.release()
cv2.destroyAllWindows()
print("Stream ditutup.")
