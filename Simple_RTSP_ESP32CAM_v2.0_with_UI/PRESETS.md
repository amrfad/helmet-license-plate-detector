# Configuration Presets

Kumpulan konfigurasi preset untuk berbagai use case ESP32-CAM.

## 🎯 Cara Menggunakan Presets

### Method 1: Via HTTP API
```bash
# Apply preset via curl
bash apply_preset.sh low_latency

# Or manual
curl "http://192.168.1.100/set_resolution?value=6"
curl "http://192.168.1.100/set_quality?value=12"
```

### Method 2: Edit Firmware Default
```cpp
// In Simple_RTSP_ESP32CAM.ino
struct CameraSettings {
    framesize_t resolution = FRAMESIZE_QVGA;  // ← Change here
    int jpegQuality = 12;                      // ← Change here
    int flashIntensity = 0;
    bool rtspRunning = false;
} cameraSettings;
```

### Method 3: Web Dashboard
Open `http://192.168.1.100/` and configure manually.

---

## 📦 Presets

### 1. 🏃 Low Latency (Real-time Monitoring)

**Use Case:** Security monitoring, robot vision, live streaming

**Settings:**
```
Resolution:  QVGA (320x240)     → value=6
Quality:     12                 → High quality
Frame Rate:  20-25 FPS
Flash:       0 (off)
```

**Performance:**
- Latency: 50-100ms
- Bandwidth: ~300 KB/s
- CPU Usage: 60-70%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=6"
curl "http://192.168.1.100/set_quality?value=12"
curl "http://192.168.1.100/set_flash?value=0"
```

**Code Modification:**
```cpp
// Optional: Increase frame rate
uint32_t msecPerFrame = 40;  // 25 FPS (was 50 = 20 FPS)
```

---

### 2. ⚖️ Balanced (General Purpose)

**Use Case:** General monitoring, video recording

**Settings:**
```
Resolution:  VGA (640x480)      → value=4
Quality:     15                 → Medium quality
Frame Rate:  15 FPS
Flash:       0 (off)
```

**Performance:**
- Latency: 100-150ms
- Bandwidth: ~600 KB/s
- CPU Usage: 70-80%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=4"
curl "http://192.168.1.100/set_quality?value=15"
curl "http://192.168.1.100/set_flash?value=0"
```

**Code Modification:**
```cpp
uint32_t msecPerFrame = 67;  // 15 FPS
```

---

### 3. 🎨 High Quality (Photography/Recording)

**Use Case:** High-quality snapshots, documentation

**Settings:**
```
Resolution:  XGA (1024x768)     → value=2
Quality:     10                 → Very high quality
Frame Rate:  10 FPS
Flash:       128 (optional)
```

**Performance:**
- Latency: 150-250ms
- Bandwidth: ~1 MB/s
- CPU Usage: 80-90%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=2"
curl "http://192.168.1.100/set_quality?value=10"
curl "http://192.168.1.100/set_flash?value=128"
```

**Code Modification:**
```cpp
uint32_t msecPerFrame = 100;  // 10 FPS
```

**Warning:** Requires good WiFi signal and power supply!

---

### 4. 📱 Low Bandwidth (Slow Network)

**Use Case:** Remote areas, 3G/4G connection, bandwidth-limited

**Settings:**
```
Resolution:  CIF (400x296)      → value=5
Quality:     25                 → Lower quality
Frame Rate:  10 FPS
Flash:       0 (off)
```

**Performance:**
- Latency: 100-200ms
- Bandwidth: ~150 KB/s
- CPU Usage: 50-60%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=5"
curl "http://192.168.1.100/set_quality?value=25"
curl "http://192.168.1.100/set_flash?value=0"
```

**Code Modification:**
```cpp
uint32_t msecPerFrame = 100;  // 10 FPS
```

**Additional Optimization:**
```cpp
// Enable WiFi power save
WiFi.setSleep(true);
```

---

### 5. 🌙 Night Vision

**Use Case:** Low-light monitoring, night surveillance

**Settings:**
```
Resolution:  QVGA (320x240)     → value=6
Quality:     10                 → High quality
Frame Rate:  15 FPS
Flash:       200 (adjustable)
```

**Performance:**
- Latency: 75-125ms
- Bandwidth: ~250 KB/s
- CPU Usage: 60-70%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=6"
curl "http://192.168.1.100/set_quality?value=10"
curl "http://192.168.1.100/set_flash?value=200"
```

**Code Modification:**
```cpp
uint32_t msecPerFrame = 67;  // 15 FPS

// Optional: Auto-enable at night
void setup() {
    // ... existing code ...
    
    // Check time and enable flash
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
        int hour = timeinfo.tm_hour;
        if (hour >= 19 || hour <= 6) {  // 7PM - 6AM
            cameraSettings.flashIntensity = 200;
            analogWrite(FLASH_LED_PIN, 200);
        }
    }
}
```

---

### 6. 🔋 Power Saving

**Use Case:** Battery-powered, solar-powered, low power mode

**Settings:**
```
Resolution:  QVGA (320x240)     → value=6
Quality:     20                 → Medium quality
Frame Rate:  5 FPS
Flash:       0 (off)
```

**Performance:**
- Latency: 200-400ms
- Bandwidth: ~100 KB/s
- CPU Usage: 30-40%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=6"
curl "http://192.168.1.100/set_quality?value=20"
curl "http://192.168.1.100/set_flash?value=0"
```

**Code Modification:**
```cpp
uint32_t msecPerFrame = 200;  // 5 FPS

// Enable WiFi sleep
WiFi.setSleep(true);

// Lower CPU frequency (optional)
setCpuFrequencyMhz(80);  // From 240MHz to 80MHz
```

**Additional Power Saving:**
```cpp
// Deep sleep when no clients
void rtspTask(void* parameter) {
    static unsigned long lastClientTime = millis();
    
    for(;;) {
        if (!streamer->anySessions()) {
            if (millis() - lastClientTime > 300000) {  // 5 minutes
                Serial.println("No clients for 5 min, entering deep sleep");
                esp_deep_sleep_start();
            }
        } else {
            lastClientTime = millis();
        }
        
        // ... rest of task ...
    }
}
```

---

### 7. 🤖 AI/ML Processing

**Use Case:** Object detection, face recognition, helmet detection

**Settings:**
```
Resolution:  VGA (640x480)      → value=4
Quality:     12                 → Good quality
Frame Rate:  10 FPS             → Give time for AI processing
Flash:       0 (auto)
```

**Performance:**
- Latency: 100-200ms (+ AI processing)
- Bandwidth: ~500 KB/s
- CPU Usage: 70% (Core 0) + AI on Core 1

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=4"
curl "http://192.168.1.100/set_quality?value=12"
curl "http://192.168.1.100/set_flash?value=0"
```

**Code Modification:**
```cpp
// Reduce FPS to give time for AI
uint32_t msecPerFrame = 100;  // 10 FPS

// Add AI task on Core 1
void aiTask(void* parameter) {
    for(;;) {
        if (xSemaphoreTake(cameraMutex, 100 / portTICK_PERIOD_MS) == pdTRUE) {
            camera_fb_t *fb = esp_camera_fb_get();
            
            if (fb) {
                // Run AI inference here
                // processImage(fb->buf, fb->len);
                
                esp_camera_fb_return(fb);
            }
            
            xSemaphoreGive(cameraMutex);
        }
        
        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

// Create AI task in setup()
xTaskCreatePinnedToCore(aiTask, "ai", 8192, NULL, 1, NULL, 1);
```

---

### 8. 📸 Timelapse

**Use Case:** Long-term monitoring, construction progress

**Settings:**
```
Resolution:  SXGA (1280x1024)   → value=1
Quality:     10                 → High quality
Frame Rate:  0.1 FPS (1 per 10s)
Flash:       0 (off)
```

**Performance:**
- Latency: N/A (not real-time)
- Bandwidth: ~10 KB/s average
- CPU Usage: 10-20%

**Apply:**
```bash
curl "http://192.168.1.100/set_resolution?value=1"
curl "http://192.168.1.100/set_quality?value=10"
curl "http://192.168.1.100/set_flash?value=0"
```

**Code Modification:**
```cpp
// In rtspTask()
uint32_t msecPerFrame = 10000;  // 1 frame per 10 seconds

// Optional: Save to SD card
#include <SD_MMC.h>

void saveTimelapse() {
    if (xSemaphoreTake(cameraMutex, portMAX_DELAY) == pdTRUE) {
        camera_fb_t *fb = esp_camera_fb_get();
        
        if (fb) {
            String filename = "/timelapse_" + String(millis()) + ".jpg";
            File file = SD_MMC.open(filename, FILE_WRITE);
            if (file) {
                file.write(fb->buf, fb->len);
                file.close();
                Serial.println("Saved: " + filename);
            }
            
            esp_camera_fb_return(fb);
        }
        
        xSemaphoreGive(cameraMutex);
    }
}
```

---

## 🔄 Dynamic Preset Switching

### Auto Preset Based on Time

```cpp
void applyPresetByTime() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) return;
    
    int hour = timeinfo.tm_hour;
    
    if (hour >= 8 && hour <= 17) {
        // Daytime: High quality
        cameraSettings.resolution = FRAMESIZE_VGA;
        cameraSettings.jpegQuality = 12;
        cameraSettings.flashIntensity = 0;
    } else if (hour >= 18 && hour <= 22) {
        // Evening: Night vision
        cameraSettings.resolution = FRAMESIZE_QVGA;
        cameraSettings.jpegQuality = 10;
        cameraSettings.flashIntensity = 200;
    } else {
        // Night: Power saving
        cameraSettings.resolution = FRAMESIZE_QVGA;
        cameraSettings.jpegQuality = 20;
        cameraSettings.flashIntensity = 0;
    }
    
    restartRTSP();
}

// Call in setup() or periodically
```

### Auto Preset Based on WiFi Signal

```cpp
void applyPresetBySignal() {
    int rssi = WiFi.RSSI();
    
    if (rssi > -50) {
        // Excellent signal: High quality
        cameraSettings.resolution = FRAMESIZE_XGA;
        cameraSettings.jpegQuality = 10;
    } else if (rssi > -70) {
        // Good signal: Balanced
        cameraSettings.resolution = FRAMESIZE_VGA;
        cameraSettings.jpegQuality = 15;
    } else {
        // Weak signal: Low bandwidth
        cameraSettings.resolution = FRAMESIZE_CIF;
        cameraSettings.jpegQuality = 25;
    }
    
    restartRTSP();
}
```

### Auto Preset Based on Client Count

```cpp
void applyPresetByClients() {
    int clientCount = 0;
    
    // Count active RTSP sessions
    LinkedListElement* current = streamer->getClientsListHead()->getNext();
    while (current != NULL) {
        clientCount++;
        current = current->getNext();
    }
    
    if (clientCount == 0) {
        // No clients: Power saving
        cameraSettings.resolution = FRAMESIZE_QVGA;
        cameraSettings.jpegQuality = 20;
    } else if (clientCount == 1) {
        // One client: High quality
        cameraSettings.resolution = FRAMESIZE_VGA;
        cameraSettings.jpegQuality = 12;
    } else {
        // Multiple clients: Low bandwidth
        cameraSettings.resolution = FRAMESIZE_CIF;
        cameraSettings.jpegQuality = 20;
    }
    
    restartRTSP();
}
```

---

## 📊 Preset Comparison Table

| Preset | Resolution | Quality | FPS | Bandwidth | Latency | Use Case |
|--------|-----------|---------|-----|-----------|---------|----------|
| Low Latency | QVGA | 12 | 20-25 | 300 KB/s | 50-100ms | Real-time |
| Balanced | VGA | 15 | 15 | 600 KB/s | 100-150ms | General |
| High Quality | XGA | 10 | 10 | 1 MB/s | 150-250ms | Photography |
| Low Bandwidth | CIF | 25 | 10 | 150 KB/s | 100-200ms | Slow network |
| Night Vision | QVGA | 10 | 15 | 250 KB/s | 75-125ms | Low light |
| Power Saving | QVGA | 20 | 5 | 100 KB/s | 200-400ms | Battery |
| AI/ML | VGA | 12 | 10 | 500 KB/s | 100-200ms | Processing |
| Timelapse | SXGA | 10 | 0.1 | 10 KB/s | N/A | Long-term |

---

## 🛠️ Preset Testing Script

Save as `test_presets.sh`:

```bash
#!/bin/bash

ESP32_IP="192.168.1.100"

presets=(
    "6,12,0,Low_Latency"
    "4,15,0,Balanced"
    "2,10,0,High_Quality"
    "5,25,0,Low_Bandwidth"
    "6,10,200,Night_Vision"
    "6,20,0,Power_Saving"
)

for preset in "${presets[@]}"; do
    IFS=',' read -r res quality flash name <<< "$preset"
    
    echo "Testing preset: $name"
    echo "Resolution: $res, Quality: $quality, Flash: $flash"
    
    curl -s "http://${ESP32_IP}/set_resolution?value=${res}"
    sleep 2
    curl -s "http://${ESP32_IP}/set_quality?value=${quality}"
    sleep 2
    curl -s "http://${ESP32_IP}/set_flash?value=${flash}"
    
    echo "Applied! Testing for 10 seconds..."
    sleep 10
    echo ""
done

echo "All presets tested!"
```

Make executable:
```bash
chmod +x test_presets.sh
./test_presets.sh
```

---

## 📝 Custom Preset Template

```cpp
// Add to Simple_RTSP_ESP32CAM.ino

void applyCustomPreset() {
    // Your custom settings
    cameraSettings.resolution = FRAMESIZE_???;  // Choose resolution
    cameraSettings.jpegQuality = ???;           // 10-63
    cameraSettings.flashIntensity = ???;        // 0-255
    
    // Optional: Adjust frame rate
    // Edit in rtspTask(): uint32_t msecPerFrame = ???;
    
    // Apply
    restartRTSP();
    
    Serial.println("Custom preset applied!");
}

// Call from HTTP endpoint
void handleCustomPreset() {
    applyCustomPreset();
    webServer.send(200, "text/plain", "Custom preset applied!");
}

// Register endpoint
void setupWebServer() {
    // ... existing endpoints ...
    webServer.on("/apply_custom", handleCustomPreset);
}
```

---

**Choose the preset that fits your use case!** 🎯
