from paddleocr import PaddleOCR

# Inisialisasi OCR
ocr = PaddleOCR(
    use_angle_cls=True,   # deteksi teks miring
    lang='en'             # ganti 'id' jika bahasa Indonesia
)

# Path ke image
image_path = "helmet-detection-system\\backend\\static\\crops\\failed_ocr_1766165246_649.jpg"

# Prediksi OCR
result = ocr.ocr(image_path)

# Tampilkan hasil
for page in result:
    for line in page["rec_texts"]:
        print(line)
