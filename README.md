# 🏍️ Helmet Detection System

Sistem deteksi helm menggunakan YOLO dan PaddleOCR untuk mendeteksi pengendara motor yang tidak memakai helm dan membaca plat nomor kendaraan.

## 📋 Deskripsi

Sistem ini terdiri dari:
- **Backend**: Flask server dengan YOLO untuk deteksi objek dan PaddleOCR untuk membaca plat nomor
- **Frontend**: React + Vite untuk antarmuka pengguna

### Fitur Utama
- ✅ Deteksi pengendara motor (rider)
- ✅ Deteksi helm / tanpa helm
- ✅ Deteksi plat nomor kendaraan
- ✅ OCR plat nomor untuk pelanggaran (tanpa helm)
- ✅ Mendukung webcam, file video, dan RTSP stream
- ✅ Log pelanggaran dengan gambar plat nomor

---

## ⚙️ Prasyarat

Pastikan Anda sudah menginstall:

- **Python 3.8+** 
- **Node.js 18+** dan npm
- **CUDA Toolkit** (opsional, untuk GPU acceleration)

---

## 🚀 Cara Menjalankan

### 1. Clone/Download Project

```bash
cd helmet-detection-system
```

### 2. Setup Backend

#### a. Buat Virtual Environment (Direkomendasikan)

```bash
cd backend
python -m venv .venv
```

#### b. Aktifkan Virtual Environment

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.\.venv\Scripts\activate.bat
```

**Linux/MacOS:**
```bash
source .venv/bin/activate
```

#### c. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** Jika ingin menggunakan GPU, install PaddlePaddle GPU:
> ```bash
> pip install paddlepaddle-gpu
> ```

#### d. Download Model YOLO (Opsional)

Sistem akan otomatis download model jika tidak ditemukan. Jika Anda memiliki model custom, letakkan di path yang sesuai dan update `detection.py`.

#### e. Jalankan Backend

```bash
python app.py
```

Backend akan berjalan di: `http://localhost:5000`

---

### 3. Setup Frontend

#### a. Buka Terminal Baru dan Masuk ke Folder Frontend

```bash
cd frontend
```

#### b. Install Dependencies

```bash
npm install
```

#### c. Jalankan Frontend

```bash
npm run dev
```

Frontend akan berjalan di: `http://localhost:5173` (atau port lain yang ditampilkan di terminal)

---

## 🖥️ Penggunaan

1. Buka browser dan akses `http://localhost:5173`
2. Pilih sumber video:
   - **Webcam**: Gunakan webcam komputer (default index: 0)
   - **File**: Upload atau masukkan path file video
   - **RTSP**: Masukkan URL RTSP stream
3. Klik tombol untuk memulai deteksi
4. Lihat hasil deteksi secara real-time di layar
5. Log pelanggaran akan tampil di panel log

---

## 📁 Struktur Project

```
helmet-detection-system/
├── backend/
│   ├── app.py              # Flask application entry point
│   ├── routes.py           # API endpoints
│   ├── detection.py        # YOLO + PaddleOCR detection logic
│   ├── camera.py           # Video source handler
│   ├── requirements.txt    # Python dependencies
│   ├── static/crops/       # Cropped license plate images
│   └── logs/               # Detection logs (JSON)
│
└── frontend/
    ├── src/
    │   ├── App.jsx         # Main React component
    │   └── components/     # UI components
    ├── package.json        # Node dependencies
    └── vite.config.js      # Vite configuration
```

---

## 🔧 Konfigurasi

### Mengubah Port Backend

Edit `backend/app.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

### Mengubah Model YOLO

Edit path di `backend/detection.py`:
```python
path_to_check = r"path/to/your/model.pt"
```

---

## ⚠️ Troubleshooting

### Webcam tidak terdeteksi
- Pastikan webcam tidak sedang digunakan aplikasi lain
- Coba ganti index webcam (0, 1, 2, dst.)

### PaddleOCR error
- Pastikan menggunakan Python 3.8-3.10
- Install ulang paddlepaddle: `pip install paddlepaddle --upgrade`

### CUDA tidak terdeteksi
- Pastikan CUDA Toolkit terinstall
- Pastikan versi CUDA kompatibel dengan PyTorch/PaddlePaddle

---

## 📄 API Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/video_feed` | GET | Stream video dengan deteksi |
| `/api/config` | POST | Konfigurasi sumber video |
| `/api/logs` | GET | Ambil log deteksi |
| `/api/status` | GET | Cek status backend |

### Contoh Request `/api/config`

```json
{
  "mode": "webcam",  // "webcam", "file", atau "rtsp"
  "value": "0"       // index webcam, path file, atau URL RTSP
}
```

---

## 📝 License

MIT License

---

## 👨‍💻 Author

Dibuat untuk mata kuliah **Pengolahan Citra Digital**
