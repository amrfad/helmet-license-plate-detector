# ESP32-CAM Dual-Core RTSP Server + HTTP Dashboard

Firmware ESP32-CAM (AI Thinker) dengan arsitektur dual-core yang memisahkan RTSP streaming dan HTTP dashboard untuk performa optimal.

## 🎯 Fitur Utama

### Arsitektur Dual-Core
- **Core 0**: RTSP Server (Real-time streaming dengan prioritas tinggi)
- **Core 1**: HTTP Web Dashboard (Konfigurasi tanpa mengganggu streaming)

### RTSP Streaming
- ✅ Stream MJPEG stabil menggunakan Micro-RTSP
- ✅ Thread-safe dengan mutex protection
- ✅ Tidak ada frame corruption saat HTTP request
- ✅ Auto-reconnect untuk multiple clients
- ✅ Frame rate 20 FPS (QVGA default)

### HTTP Dashboard
- 🖼️ **Pengaturan Resolusi**: UXGA, SXGA, XGA, SVGA, VGA, CIF, QVGA
- ⚙️ **JPEG Quality**: 10-63 (lower = better quality)
- 💡 **LED Flash Control**: 0-255 intensity
- 📊 **JSON API**: `/status` endpoint untuk monitoring
- 🎨 **Simple UI**: Responsive HTML interface

### Keamanan Thread
- Mutex protection untuk akses kamera
- Safe camera reconfiguration
- RTSP restart otomatis saat ubah settings

## 📋 Requirements

### Hardware
- ESP32-CAM AI Thinker (dengan PSRAM)
- Programmer (FTDI atau USB-to-TTL)
- Power supply 5V minimal 2A

### Software
- PlatformIO (recommended) atau Arduino IDE
- VLC Media Player atau RTSP client lainnya
- Web browser untuk dashboard

## 🚀 Quick Start

### 1. Konfigurasi WiFi
Edit file `Simple_RTSP_ESP32CAM.ino`:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

### 2. Upload ke ESP32-CAM
**PlatformIO:**
```bash
pio run --target upload
pio device monitor
```

**Arduino IDE:**
1. Install ESP32 board support
2. Select board: "AI Thinker ESP32-CAM"
3. Upload sketch
4. Open Serial Monitor (115200 baud)

### 3. Akses RTSP Stream
Setelah upload, cek Serial Monitor untuk IP address, lalu:

**VLC Player:**
1. Media → Open Network Stream
2. URL: `rtsp://192.168.x.x:8554/mjpeg/1`
3. Show more options
4. Edit Options: `:network-caching=1000 --rtsp-tcp`

**FFplay:**
```bash
ffplay -rtsp_transport tcp rtsp://192.168.x.x:8554/mjpeg/1
```

### 4. Akses HTTP Dashboard
Buka browser: `http://192.168.x.x/`

## 🔧 API Endpoints

### GET /status
Mendapatkan status konfigurasi saat ini
```json
{
  "resolution": 6,
  "quality": 12,
  "flash": 0,
  "rtsp_running": true
}
```

### GET /set_resolution?value=X
Mengubah resolusi kamera (0-6):
- 0 = UXGA (1600x1200)
- 1 = SXGA (1280x1024)
- 2 = XGA (1024x768)
- 3 = SVGA (800x600)
- 4 = VGA (640x480)
- 5 = CIF (400x296)
- 6 = QVGA (320x240) - **Default**

**Response:** `Resolusi berhasil diubah! RTSP di-restart.`

### GET /set_quality?value=X
Mengubah JPEG quality (10-63, lower = better)

**Response:** `Quality berhasil diubah! RTSP di-restart.`

### GET /set_flash?value=X
Mengubah LED flash intensity (0-255)

**Response:** `Flash intensity berhasil diubah!`

## 🏗️ Struktur Kode

### Global Variables
```cpp
OV2640 cam;                           // Camera driver
WiFiServer rtspServer(8554);          // RTSP server
WebServer webServer(80);              // HTTP server
CStreamer *streamer;                  // RTSP streamer
SemaphoreHandle_t cameraMutex;        // Mutex untuk camera access
```

### FreeRTOS Tasks
```cpp
xTaskCreatePinnedToCore(rtspTask, "rtsp", 8192, NULL, 2, NULL, 0);
xTaskCreatePinnedToCore(webTask,  "web",  8192, NULL, 1, NULL, 1);
```

### Key Functions
- `rtspTask()`: Handle RTSP streaming di Core 0
- `webTask()`: Handle HTTP requests di Core 1
- `restartRTSP()`: Safe RTSP restart dengan mutex
- `applyCameraSettings()`: Apply settings thread-safe

## ⚙️ Konfigurasi Lanjutan

### Frame Rate
Edit di `rtspTask()`:
```cpp
uint32_t msecPerFrame = 50;  // 20 FPS
// 15 FPS = 67ms, 20 FPS = 50ms, 25 FPS = 40ms, 30 FPS = 33ms
```

### Task Stack Size
Jika mengalami stack overflow, tingkatkan:
```cpp
xTaskCreatePinnedToCore(rtspTask, "rtsp", 16384, ...);  // 16KB
```

### LED Flash Pin
Default GPIO 4 (AI Thinker):
```cpp
#define FLASH_LED_PIN 4
```

## 🐛 Troubleshooting

### RTSP tidak bisa connect
- Pastikan menggunakan `--rtsp-tcp` flag
- Cek firewall/router settings
- Gunakan IP static di router

### Frame patah/corrupt
- Turunkan resolusi ke QVGA/CIF
- Tingkatkan JPEG quality (nilai lebih kecil)
- Cek kualitas power supply

### Kamera gagal init
- Pastikan menggunakan AI Thinker board
- Cek koneksi kamera module
- Reset ESP32-CAM dan upload ulang

### Web dashboard lambat
- Normal jika RTSP sedang streaming
- Web task priority lebih rendah (by design)
- Refresh manual jika perlu

## 📊 Performance Notes

### Recommended Settings
- **QVGA (320x240)**: 20-30 FPS, latency rendah
- **VGA (640x480)**: 15-20 FPS, balanced
- **XGA (1024x768)**: 10-15 FPS, quality tinggi

### Memory Usage
- RTSP Task: ~8KB stack
- Web Task: ~8KB stack
- Total heap: ~200KB (with PSRAM)

## 🔐 Security

**PERINGATAN**: Firmware ini tidak memiliki autentikasi!

Untuk production:
- Tambahkan WiFi AP mode dengan WPA2
- Implementasi HTTP Basic Auth
- Gunakan HTTPS/RTSPS
- Batasi akses dengan firewall

## 📝 License

MIT License - Gunakan dengan bebas

## 🙏 Credits

- [Micro-RTSP](https://github.com/geeksville/Micro-RTSP) - RTSP implementation
- [esp_camera](https://github.com/espressif/esp32-camera) - ESP32 camera driver
- FreeRTOS - Real-time OS

## 📧 Support

Jika ada masalah:
1. Cek Serial Monitor untuk error messages
2. Pastikan power supply mencukupi (min 2A)
3. Gunakan board ESP32-CAM yang genuine

---

**Happy Streaming! 🎥**