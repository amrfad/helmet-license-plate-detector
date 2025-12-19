# Arsitektur Dual-Core ESP32-CAM

## 📐 Diagram Arsitektur

```
┌─────────────────────────────────────────────────────────────┐
│                      ESP32-CAM System                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────┐        ┌───────────────────┐         │
│  │   CORE 0          │        │   CORE 1          │         │
│  │  (Real-time)      │        │  (Background)     │         │
│  ├───────────────────┤        ├───────────────────┤         │
│  │                   │        │                   │         │
│  │  rtspTask()       │        │  webTask()        │         │
│  │  Priority: 2      │        │  Priority: 1      │         │
│  │  Stack: 8KB       │        │  Stack: 8KB       │         │
│  │                   │        │                   │         │
│  │  • handleRequests │        │  • handleClient() │         │
│  │  • streamImage()  │        │  • HTTP endpoints │         │
│  │  • acceptClients  │        │  • JSON API       │         │
│  │                   │        │                   │         │
│  └─────────┬─────────┘        └─────────┬─────────┘         │
│            │                            │                   │
│            └────────────┬───────────────┘                   │
│                         │                                   │
│                    ┌────▼────┐                              │
│                    │  Mutex  │                              │
│                    │ (Semap) │                              │
│                    └────┬────┘                              │
│                         │                                   │
│                    ┌────▼────────┐                          │
│                    │   OV2640    │                          │
│                    │   Camera    │                          │
│                    │   Driver    │                          │
│                    └─────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 🔄 Flow Diagram

### RTSP Streaming Flow (Core 0)
```
┌──────────────┐
│ Start RTSP   │
│ Task (Core 0)│
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Listen for new   │
│ RTSP clients     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐      Yes    ┌─────────────────┐
│ Client connected?├─────────────►│ Add new session │
└──────┬───────────┘              └─────────────────┘
       │ No
       ▼
┌──────────────────┐
│ Handle existing  │
│ client requests  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐      Yes    ┌──────────────────┐
│ Time to send     ├─────────────►│ Take mutex       │
│ next frame?      │              └─────┬────────────┘
└──────────────────┘                    │
                                        ▼
                                 ┌──────────────────┐
                                 │ Capture & stream │
                                 │ JPEG frame       │
                                 └─────┬────────────┘
                                       │
                                       ▼
                                 ┌──────────────────┐
                                 │ Release mutex    │
                                 └──────────────────┘
```

### HTTP Configuration Flow (Core 1)
```
┌──────────────┐
│ Start Web    │
│ Task (Core 1)│
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Wait for HTTP    │
│ client request   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Parse endpoint:  │
│ /status          │◄──── GET status
│ /set_resolution  │◄──── Change resolution
│ /set_quality     │◄──── Change quality
│ /set_flash       │◄──── Control LED
└──────┬───────────┘
       │
       ▼
┌──────────────────┐      Config change?
│ Need restart     ├─────────┐
│ RTSP?            │         │ Yes
└──────┬───────────┘         │
       │ No                  ▼
       │              ┌──────────────────┐
       │              │ Call restartRTSP │
       │              └─────┬────────────┘
       │                    │
       │                    ▼
       │              ┌──────────────────┐
       │              │ Stop streaming   │
       │              └─────┬────────────┘
       │                    │
       │                    ▼
       │              ┌──────────────────┐
       │              │ Take mutex       │
       │              └─────┬────────────┘
       │                    │
       │                    ▼
       │              ┌──────────────────┐
       │              │ Delete streamer  │
       │              └─────┬────────────┘
       │                    │
       │                    ▼
       │              ┌──────────────────┐
       │              │ Apply new config │
       │              └─────┬────────────┘
       │                    │
       │                    ▼
       │              ┌──────────────────┐
       │              │ Create streamer  │
       │              └─────┬────────────┘
       │                    │
       │                    ▼
       │              ┌──────────────────┐
       │              │ Release mutex    │
       │              └─────┬────────────┘
       │                    │
       └────────────────────┘
                            │
                            ▼
                     ┌──────────────────┐
                     │ Send HTTP        │
                     │ response         │
                     └──────────────────┘
```

## 🔒 Thread Safety dengan Mutex

### Kenapa Pakai Mutex?
ESP32 adalah dual-core processor. Tanpa mutex, kedua core bisa mengakses kamera secara bersamaan, menyebabkan:
- **Data corruption** (frame rusak)
- **Crash/panic** (reset ESP32)
- **Race condition** (hasil tidak predictable)

### Mutex Implementation
```cpp
// Global mutex
SemaphoreHandle_t cameraMutex;

// Di setup()
cameraMutex = xSemaphoreCreateMutex();

// Saat akses kamera (RTSP Core 0)
if (xSemaphoreTake(cameraMutex, 10 / portTICK_PERIOD_MS) == pdTRUE) {
    streamer->streamImage(now);  // Safe!
    xSemaphoreGive(cameraMutex);
}

// Saat restart RTSP (HTTP Core 1)
if (xSemaphoreTake(cameraMutex, portMAX_DELAY) == pdTRUE) {
    delete streamer;
    // Apply new settings
    streamer = new OV2640Streamer(&cam);
    xSemaphoreGive(cameraMutex);
}
```

### Mutex Flow
```
RTSP Task (Core 0)          Mutex           HTTP Task (Core 1)
─────────────────          ───────          ──────────────────
      │                                              │
      │ Take mutex (10ms timeout)                    │
      ├──────────────────►[LOCKED]                   │
      │                      │                       │
      │ Stream frame         │                       │
      │                      │                       │
      │                      │    Take mutex (wait forever)
      │                      │◄──────────────────────┤
      │                      │    [WAITING...]       │
      │ Release mutex        │                       │
      ├──────────────────►[UNLOCKED]                 │
      │                      │                       │
      │                      ├──────────────────────►│
      │                      │ [LOCKED]     Got mutex!
      │                      │                       │
      │ Take mutex (10ms)    │                       │
      ├──────────────────►[BUSY]                     │
      │ Timeout! Skip frame  │                       │
      │                      │         Restart RTSP  │
      │                      │                       │
      │                      │◄──────────────────────┤
      │                      │ [UNLOCKED]  Release   │
      ▼                      ▼                       ▼
```

## 📊 Memory Management

### Stack Allocation
```cpp
// RTSP Task - 8KB stack
xTaskCreatePinnedToCore(rtspTask, "rtsp", 8192, NULL, 2, NULL, 0);
//                                          ^^^^
//                                        8192 bytes

// Web Task - 8KB stack  
xTaskCreatePinnedToCore(webTask, "web", 8192, NULL, 1, NULL, 1);
```

### Heap Usage
- **Camera driver**: ~100KB (PSRAM)
- **WiFi stack**: ~40KB
- **RTSP sessions**: ~10KB per client
- **HTTP server**: ~20KB
- **Total free heap**: ~200KB (depends on PSRAM)

### PSRAM Importance
ESP32-CAM **HARUS** punya PSRAM karena:
- Frame buffer QVGA JPEG: ~20-40KB
- Frame buffer VGA JPEG: ~60-100KB
- Frame buffer XGA JPEG: ~100-200KB

## ⚡ Performance Optimization

### Core Pinning Strategy
```
Core 0 (PRO_CPU):
✅ RTSP task (Priority 2)
   - Time-critical
   - Consistent frame delivery
   - Minimal latency

Core 1 (APP_CPU):
✅ Web task (Priority 1)
✅ WiFi stack
✅ Arduino loop()
   - Background work
   - OK to have latency
```

### Priority Levels
```
Priority 2: RTSP (real-time streaming)
Priority 1: HTTP (configuration)
Priority 0: Idle task (cleanup)
```

### Frame Rate Control
```cpp
uint32_t msecPerFrame = 50;  // 20 FPS

// Adaptive frame rate based on resolution:
switch(resolution) {
    case FRAMESIZE_QVGA: msecPerFrame = 50;  break;  // 20 FPS
    case FRAMESIZE_VGA:  msecPerFrame = 67;  break;  // 15 FPS
    case FRAMESIZE_XGA:  msecPerFrame = 100; break;  // 10 FPS
}
```

## 🔧 Safe Reconfiguration

### Problem
Mengubah resolusi/quality saat streaming bisa menyebabkan:
- Frame corruption
- Client disconnect
- ESP32 crash

### Solution: restartRTSP()
```cpp
void restartRTSP() {
    // Step 1: Signal stop
    cameraSettings.rtspRunning = false;
    vTaskDelay(100);  // Wait for RTSP task to stop
    
    // Step 2: Take mutex (block RTSP)
    xSemaphoreTake(cameraMutex, portMAX_DELAY);
    
    // Step 3: Clean up
    delete streamer;
    
    // Step 4: Apply new settings
    sensor_t *s = esp_camera_sensor_get();
    s->set_framesize(s, cameraSettings.resolution);
    s->set_quality(s, cameraSettings.jpegQuality);
    
    // Step 5: Recreate
    streamer = new OV2640Streamer(&cam);
    cameraSettings.rtspRunning = true;
    
    // Step 6: Release mutex
    xSemaphoreGive(cameraMutex);
}
```

### Sequence Diagram
```
HTTP Request       Core 1 Task        Mutex        Core 0 Task
─────────────     ────────────       ───────      ────────────
     │                 │                              │
     │ /set_resolution │                              │
     ├────────────────►│                              │
     │                 │                              │
     │                 │ rtspRunning = false          │
     │                 ├─────────────────────────────►│
     │                 │                              │ Stop streaming
     │                 │                              │
     │                 │ Take mutex                   │
     │                 ├────────────►[LOCKED]         │
     │                 │                │             │
     │                 │ Delete         │             │ Try take mutex
     │                 │ streamer       │             ├──►[BUSY] Timeout
     │                 │                │             │
     │                 │ Apply          │             │ Skip frame
     │                 │ settings       │             │
     │                 │                │             │
     │                 │ Create new     │             │
     │                 │ streamer       │             │
     │                 │                │             │
     │                 │ Release mutex  │             │
     │                 ├────────────►[UNLOCKED]       │
     │                 │                │             │
     │                 │                │ Take mutex  │
     │                 │                ◄─────────────┤
     │                 │                │  [LOCKED]   │
     │ Response OK     │                │             │ Resume stream
     ◄─────────────────┤                │             │ (new config)
     │                 │                │             │
```

## 🎯 Best Practices

### 1. Mutex Timeout
```cpp
// RTSP: Short timeout (jangan block streaming)
xSemaphoreTake(cameraMutex, 10 / portTICK_PERIOD_MS);

// HTTP: Long timeout (OK to wait)
xSemaphoreTake(cameraMutex, portMAX_DELAY);
```

### 2. Task Delays
```cpp
// RTSP: Minimal delay
vTaskDelay(1 / portTICK_PERIOD_MS);  // 1ms

// HTTP: Longer delay (save CPU)
vTaskDelay(10 / portTICK_PERIOD_MS); // 10ms
```

### 3. Error Handling
```cpp
if (xSemaphoreTake(cameraMutex, timeout) == pdTRUE) {
    // Critical section
    xSemaphoreGive(cameraMutex);
} else {
    // Timeout - skip this operation
    Serial.println("Mutex timeout!");
}
```

### 4. Stack Monitoring
```cpp
void rtspTask(void* parameter) {
    for(;;) {
        // Your code...
        
        // Monitor stack usage
        UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL);
        if (uxHighWaterMark < 1024) {
            Serial.printf("RTSP stack low: %d bytes\n", uxHighWaterMark);
        }
    }
}
```

## 📈 Performance Metrics

### Typical Performance (QVGA @ 20 FPS)
- **CPU Core 0**: 60-70% utilization
- **CPU Core 1**: 10-20% utilization
- **Frame latency**: 50-100ms
- **Network bandwidth**: ~200-400 KB/s
- **Free heap**: ~180KB

### Resolution Impact
| Resolution | FPS | Frame Size | Bandwidth | Latency |
|-----------|-----|------------|-----------|---------|
| QVGA      | 20  | 15-20 KB   | 300 KB/s  | 50ms    |
| VGA       | 15  | 40-60 KB   | 600 KB/s  | 100ms   |
| XGA       | 10  | 80-120 KB  | 1 MB/s    | 200ms   |

## 🚀 Future Improvements

### Possible Enhancements
1. **Multiple RTSP streams** (different resolutions)
2. **Motion detection** dengan interrupt
3. **WiFi AP mode** untuk direct connect
4. **OTA updates** via HTTP
5. **Authentication** (HTTP Basic Auth)
6. **WebSocket** untuk real-time config
7. **SD card recording** (jika ada slot)
8. **IR LED control** untuk night vision

### Advanced Features
```cpp
// Motion detection on Core 0
void motionDetectionTask(void* param) {
    // Compare frames, trigger alert
}

// OTA update on Core 1  
void otaUpdateTask(void* param) {
    // Download & flash firmware
}
```

---

**Arsitektur ini memastikan RTSP streaming stabil tanpa terpengaruh HTTP requests!** 🎯
