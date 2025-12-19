# Troubleshooting Guide

## 🔍 Diagnostic Checklist

### Serial Monitor Output
Setelah upload firmware, Serial Monitor (115200 baud) harus menampilkan:
```
=================================
ESP32-CAM Dual-Core RTSP + HTTP
=================================

Mutex berhasil dibuat
Menginisialisasi kamera...
Kamera berhasil diinisialisasi!
Resolusi: QVGA, Quality: 12

Menghubungkan ke WiFi: [SSID] ...... TERHUBUNG!
IP Address: 192.168.1.100
Signal Strength (RSSI): -45 dBm

=================================
SISTEM SIAP!
=================================
RTSP URL: rtsp://192.168.1.100:8554/mjpeg/1
HTTP Dashboard: http://192.168.1.100/
JSON Status: http://192.168.1.100/status
=================================

RTSP Task dimulai di Core 0
Web Task dimulai di Core 1
[RTSP Task] Memulai RTSP Server...
[RTSP Task] RTSP Server aktif di Core 0
[Web Task] Memulai HTTP Server...
[Web Task] HTTP Server aktif di Core 1
```

## ❌ Common Errors

### 1. Kamera Gagal Inisialisasi

**Error Message:**
```
Gagal menginisialisasi kamera! Error: 0x105
```

**Penyebab:**
- Kabel kamera tidak terpasang dengan benar
- Kamera module rusak
- Power supply tidak cukup
- Pin konfigurasi salah

**Solusi:**
```cpp
// 1. Cek koneksi fisik kamera
// 2. Pastikan menggunakan AI Thinker config
esp_err_t err = cam.init(esp32cam_aithinker_config);

// 3. Jika tetap gagal, tambahkan delay
delay(1000);
esp_err_t err = cam.init(esp32cam_aithinker_config);

// 4. Cek power supply - minimal 5V 2A
// 5. Hard reset ESP32-CAM (tekan tombol reset)
```

**Error Codes:**
- `0x105` (ESP_ERR_NOT_FOUND): Kamera tidak terdeteksi
- `0x103` (ESP_ERR_TIMEOUT): Timeout komunikasi I2C
- `0x101` (ESP_FAIL): Konfigurasi gagal

### 2. WiFi Tidak Terhubung

**Error Message:**
```
Menghubungkan ke WiFi: MyWiFi ..................
[stuck here forever]
```

**Penyebab:**
- SSID atau password salah
- WiFi terlalu jauh
- WiFi 5GHz (ESP32 hanya support 2.4GHz)
- Channel WiFi tidak supported

**Solusi:**
```cpp
// 1. Verifikasi credentials
const char* ssid = "YourSSID";        // Case-sensitive!
const char* password = "YourPassword"; // Cek spasi/karakter khusus

// 2. Tambahkan timeout
WiFi.begin(ssid, password);
int timeout = 0;
while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    Serial.print(".");
    timeout++;
}

if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWiFi gagal connect! Restart ESP32...");
    ESP.restart();
}

// 3. Set WiFi channel manual (jika perlu)
WiFi.begin(ssid, password, 6); // Force channel 6

// 4. Disable power saving
WiFi.setSleep(false);
```

**WiFi Troubleshooting:**
```bash
# Cek WiFi channel di router (harus 1-11)
# ESP32 tidak support channel 12-14

# Test dengan smartphone hotspot dulu
# untuk isolasi masalah router
```

### 3. RTSP Client Tidak Bisa Connect

**Symptoms:**
- VLC error: "Your input can't be opened"
- FFplay: "Connection refused"
- Timeout saat connect

**Penyebab:**
- Firewall blocking port 8554
- RTSP task crash
- Network issue
- RTSP URL salah

**Solusi:**

**1. Verifikasi RTSP Task Running:**
```
[RTSP Task] RTSP Server aktif di Core 0
```

**2. Test dengan telnet:**
```bash
telnet 192.168.1.100 8554
```
Jika connect, RTSP server aktif.

**3. VLC Configuration:**
```
Media → Open Network Stream
URL: rtsp://192.168.1.100:8554/mjpeg/1

✅ Show more options
Edit Options: :network-caching=1000 --rtsp-tcp

PENTING: Harus pakai --rtsp-tcp (bukan UDP)!
```

**4. FFplay Alternative:**
```bash
# Recommended (TCP)
ffplay -rtsp_transport tcp rtsp://192.168.1.100:8554/mjpeg/1

# With low latency
ffplay -rtsp_transport tcp -fflags nobuffer -flags low_delay rtsp://192.168.1.100:8554/mjpeg/1
```

**5. Cek Serial Monitor:**
```
[RTSP Task] Client baru: 192.168.1.50
```
Jika tidak muncul, client tidak sampai ke ESP32.

### 4. Frame Corruption / Rusak

**Symptoms:**
- Frame patah-patah
- Warna aneh (pink/green)
- Partial image
- "Blocky" artifacts

**Penyebab:**
- Power supply tidak stabil
- Resolusi terlalu tinggi
- JPEG quality terlalu tinggi (nilai terlalu besar)
- Bandwidth WiFi kurang
- Mutex timeout

**Solusi:**

**1. Turunkan Resolusi:**
```cpp
cameraSettings.resolution = FRAMESIZE_QVGA;  // Start here
// Jangan langsung UXGA/SXGA
```

**2. Improve JPEG Quality:**
```cpp
cameraSettings.jpegQuality = 10;  // Lower = better quality
// Range: 10-63 (jangan > 63)
```

**3. Stabilkan Power:**
```
- Gunakan power supply 5V 2A (minimal)
- Jangan powered dari USB computer
- Tambahkan kapasitor 100uF di pin 5V
- Cabut device USB lain
```

**4. Cek Mutex Timeout di Serial:**
```
Mutex timeout!  // Bad sign
```

Increase timeout:
```cpp
xSemaphoreTake(cameraMutex, 50 / portTICK_PERIOD_MS); // 10→50ms
```

**5. Reduce Frame Rate:**
```cpp
uint32_t msecPerFrame = 100;  // 10 FPS instead of 20
```

### 5. ESP32 Crash / Restart Loop

**Error Message:**
```
Guru Meditation Error: Core 0 panic'ed (LoadProhibited)
```

**Penyebab:**
- Stack overflow
- Heap exhausted
- Race condition
- NULL pointer dereference

**Solusi:**

**1. Increase Stack Size:**
```cpp
xTaskCreatePinnedToCore(rtspTask, "rtsp", 16384, NULL, 2, NULL, 0);
//                                        ^^^^^ 8192 → 16384
```

**2. Monitor Stack Usage:**
```cpp
void rtspTask(void* parameter) {
    for(;;) {
        // ... your code ...
        
        UBaseType_t stack = uxTaskGetStackHighWaterMark(NULL);
        Serial.printf("[RTSP] Free stack: %d bytes\n", stack);
    }
}
```

**3. Check Heap:**
```cpp
Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
Serial.printf("Min free heap: %d bytes\n", ESP.getMinFreeHeap());
```

**4. Enable Debug:**
```cpp
// platformio.ini
build_flags = 
    -DCORE_DEBUG_LEVEL=5  // 0→5 untuk verbose
```

**5. Add Watchdog:**
```cpp
void rtspTask(void* parameter) {
    for(;;) {
        esp_task_wdt_reset();  // Feed watchdog
        // ... task code ...
    }
}
```

### 6. HTTP Dashboard Tidak Muncul

**Symptoms:**
- Browser timeout
- "Connection refused"
- Blank page

**Solusi:**

**1. Cek Serial Monitor:**
```
[Web Task] HTTP Server aktif di Core 1
```

**2. Test dengan curl:**
```bash
curl http://192.168.1.100/status
# Should return: {"resolution":6,"quality":12,...}
```

**3. Browser Console (F12):**
Check for JavaScript errors.

**4. Verify Web Task Running:**
```cpp
Serial.printf("[Web Task] Running on core %d\n", xPortGetCoreID());
```

**5. Increase Web Task Stack:**
```cpp
xTaskCreatePinnedToCore(webTask, "web", 12288, NULL, 1, NULL, 1);
//                                      ^^^^^ 8192 → 12288
```

### 7. Settings Tidak Tersimpan

**Symptoms:**
- Ubah resolusi, kembali ke QVGA
- Quality reset setelah reboot

**Penyebab:**
Settings tidak disimpan di flash (by design).

**Solusi:**

**Add EEPROM/Preferences:**
```cpp
#include <Preferences.h>

Preferences prefs;

void saveSettings() {
    prefs.begin("camera", false);
    prefs.putInt("resolution", cameraSettings.resolution);
    prefs.putInt("quality", cameraSettings.jpegQuality);
    prefs.putInt("flash", cameraSettings.flashIntensity);
    prefs.end();
}

void loadSettings() {
    prefs.begin("camera", true);
    cameraSettings.resolution = (framesize_t)prefs.getInt("resolution", FRAMESIZE_QVGA);
    cameraSettings.jpegQuality = prefs.getInt("quality", 12);
    cameraSettings.flashIntensity = prefs.getInt("flash", 0);
    prefs.end();
}

// Call loadSettings() in setup()
// Call saveSettings() after changing config
```

### 8. Mutex Deadlock

**Symptoms:**
- ESP32 hang/freeze
- No response
- No crash, just stuck

**Diagnosis:**
```cpp
// Add timeout monitoring
unsigned long mutexWaitStart = millis();
if (xSemaphoreTake(cameraMutex, timeout) == pdTRUE) {
    // Got mutex
    xSemaphoreGive(cameraMutex);
} else {
    unsigned long waitTime = millis() - mutexWaitStart;
    Serial.printf("Mutex wait: %lu ms - DEADLOCK?\n", waitTime);
}
```

**Solusi:**
```cpp
// 1. Always release mutex
if (xSemaphoreTake(cameraMutex, timeout) == pdTRUE) {
    try {
        // Critical section
    } finally {
        xSemaphoreGive(cameraMutex);  // ← HARUS dipanggil!
    }
}

// 2. Use shorter timeouts
// RTSP: 10ms max
// HTTP: 5000ms max (portMAX_DELAY bisa berbahaya)
```

## 🔧 Advanced Debugging

### Enable Verbose Logging

**platformio.ini:**
```ini
build_flags = 
    -DCORE_DEBUG_LEVEL=5
    -DLOG_LOCAL_LEVEL=ESP_LOG_VERBOSE
```

**Code:**
```cpp
void setup() {
    esp_log_level_set("*", ESP_LOG_VERBOSE);
    esp_log_level_set("camera", ESP_LOG_VERBOSE);
}
```

### Monitor Task Performance

```cpp
void printTaskStats() {
    char statsBuffer[512];
    vTaskGetRunTimeStats(statsBuffer);
    Serial.println(statsBuffer);
}

// Call every 10 seconds
```

### Memory Leak Detection

```cpp
void checkMemoryLeak() {
    static size_t lastHeap = 0;
    size_t currentHeap = ESP.getFreeHeap();
    
    if (lastHeap > 0) {
        int diff = currentHeap - lastHeap;
        if (diff < -1024) {  // Lost 1KB
            Serial.printf("WARNING: Memory leak detected! Lost %d bytes\n", -diff);
        }
    }
    
    lastHeap = currentHeap;
}
```

### Network Debugging

**Wireshark Filter:**
```
ip.addr == 192.168.1.100 && (tcp.port == 8554 || tcp.port == 80)
```

**RTSP Handshake Test:**
```bash
# Manual RTSP handshake
telnet 192.168.1.100 8554

# Type:
OPTIONS rtsp://192.168.1.100:8554/mjpeg/1 RTSP/1.0
CSeq: 1

# Should get: RTSP/1.0 200 OK
```

## 📊 Performance Optimization

### If RTSP Lags

```cpp
// 1. Increase RTSP task priority
xTaskCreatePinnedToCore(rtspTask, "rtsp", 8192, NULL, 3, NULL, 0);
//                                                      ^ 2→3

// 2. Decrease frame rate
uint32_t msecPerFrame = 67;  // 15 FPS

// 3. Reduce resolution
cameraSettings.resolution = FRAMESIZE_CIF;

// 4. Disable WiFi power save
WiFi.setSleep(false);
```

### If HTTP Slow

```cpp
// HTTP is intentionally lower priority
// This is by design to not block RTSP

// If needed, increase priority:
xTaskCreatePinnedToCore(webTask, "web", 8192, NULL, 2, NULL, 1);
//                                                    ^ 1→2
// WARNING: May affect RTSP stability!
```

## 🚨 Emergency Recovery

### Hard Reset
1. Disconnect power
2. Wait 10 seconds
3. Reconnect power
4. Re-upload firmware

### Factory Reset Code
```cpp
#include <Preferences.h>

void factoryReset() {
    Preferences prefs;
    prefs.begin("camera", false);
    prefs.clear();
    prefs.end();
    
    ESP.restart();
}

// Call via HTTP endpoint or button
```

### Fallback Mode
```cpp
void setup() {
    // Try normal init
    esp_err_t err = cam.init(esp32cam_aithinker_config);
    
    if (err != ESP_OK) {
        Serial.println("Normal init failed, trying fallback...");
        
        // Fallback to lowest resolution
        sensor_t *s = esp_camera_sensor_get();
        if (s) {
            s->set_framesize(s, FRAMESIZE_QVGA);
            s->set_quality(s, 20);  // Lower quality
        }
    }
}
```

## 📞 Getting Help

Jika masalah masih berlanjut, kumpulkan info berikut:

### System Info
```cpp
void printSystemInfo() {
    Serial.println("\n=== SYSTEM INFO ===");
    Serial.printf("ESP32 Chip: %s Rev %d\n", ESP.getChipModel(), ESP.getChipRevision());
    Serial.printf("CPU Freq: %d MHz\n", ESP.getCpuFreqMHz());
    Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
    Serial.printf("PSRAM: %d bytes\n", ESP.getPsramSize());
    Serial.printf("Flash: %d bytes\n", ESP.getFlashChipSize());
    Serial.printf("SDK: %s\n", ESP.getSdkVersion());
    Serial.println("==================\n");
}
```

### Camera Info
```cpp
void printCameraInfo() {
    sensor_t *s = esp_camera_sensor_get();
    if (s) {
        Serial.println("\n=== CAMERA INFO ===");
        Serial.printf("PID: 0x%02X\n", s->id.PID);
        Serial.printf("Model: %s\n", s->id.PID == OV2640_PID ? "OV2640" : "Unknown");
        Serial.printf("Resolution: %d\n", s->status.framesize);
        Serial.printf("Quality: %d\n", s->status.quality);
        Serial.println("===================\n");
    }
}
```

### Share Output
Post complete Serial Monitor output dari boot sampai error terjadi.

---

**Untuk pertanyaan lebih lanjut, attach:**
1. Complete serial output
2. System info
3. Camera info
4. Steps to reproduce
5. Photo hardware setup (jika suspect power/wiring)

**Happy Debugging! 🔍**
