# 📋 Quick Reference Card

## 🚀 Upload & Setup (5 Minutes)

### Step 1: Edit WiFi Credentials
```cpp
// In Simple_RTSP_ESP32CAM.ino
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
```

### Step 2: Upload Firmware
**PlatformIO:**
```bash
pio run --target upload
pio device monitor
```

**Arduino IDE:**
- Board: "AI Thinker ESP32-CAM"
- Partition: "Huge APP (3MB)"
- Upload Speed: 921600
- Serial Monitor: 115200 baud

### Step 3: Get IP Address
Check Serial Monitor output:
```
IP Address: 192.168.1.XXX
```

### Step 4: Access Services
- **RTSP Stream**: `rtsp://192.168.1.XXX:8554/mjpeg/1`
- **HTTP Dashboard**: `http://192.168.1.XXX/`
- **JSON API**: `http://192.168.1.XXX/status`

---

## 🎥 VLC Setup (One-Time)

1. Media → Open Network Stream
2. URL: `rtsp://192.168.1.XXX:8554/mjpeg/1`
3. ✅ Show more options
4. Edit Options: `:network-caching=1000 --rtsp-tcp`
5. Play

**Important**: Always use `--rtsp-tcp` flag!

---

## 🔧 HTTP API Quick Reference

| Endpoint | Method | Parameters | Action |
|----------|--------|-----------|---------|
| `/status` | GET | - | Get current status |
| `/set_resolution?value=X` | GET | `value`: 0-6 | Change resolution |
| `/set_quality?value=X` | GET | `value`: 10-63 | Change JPEG quality |
| `/set_flash?value=X` | GET | `value`: 0-255 | Control LED flash |
| `/` | GET | - | HTML Dashboard |

### Resolution Values
```
0 = UXGA (1600x1200)
1 = SXGA (1280x1024)
2 = XGA  (1024x768)
3 = SVGA (800x600)
4 = VGA  (640x480)
5 = CIF  (400x296)
6 = QVGA (320x240) ← Default
```

### Example API Calls
```bash
# Get status
curl http://192.168.1.XXX/status

# Set VGA resolution
curl "http://192.168.1.XXX/set_resolution?value=4"

# Set high quality
curl "http://192.168.1.XXX/set_quality?value=10"

# Turn on flash at 50%
curl "http://192.168.1.XXX/set_flash?value=128"
```

---

## ⚙️ Default Configuration

```cpp
Resolution:      QVGA (320x240)
JPEG Quality:    12 (lower = better)
Flash Intensity: 0 (off)
Frame Rate:      20 FPS
RTSP Port:       8554
HTTP Port:       80
LED Flash Pin:   GPIO 4
```

---

## 🏗️ Dual-Core Architecture

```
┌─────────────────────────────────────┐
│ Core 0 (PRO_CPU) - Priority 2       │
│ ----------------------------------- │
│ • RTSP Server (Real-time)           │
│ • Handle client connections         │
│ • Stream JPEG frames                │
│ • 20 FPS @ QVGA                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Core 1 (APP_CPU) - Priority 1       │
│ ----------------------------------- │
│ • HTTP Web Server                   │
│ • Configuration endpoints           │
│ • JSON API                          │
│ • Dashboard UI                      │
└─────────────────────────────────────┘

         🔒 Mutex Protection
              (Thread-safe)
```

---

## 🔍 Common Commands

### Compile & Upload
```bash
# PlatformIO
pio run                    # Compile
pio run -t upload          # Upload
pio device monitor         # Serial monitor
pio run -t clean           # Clean build

# Arduino IDE
Ctrl+R  # Verify
Ctrl+U  # Upload
Ctrl+Shift+M  # Serial Monitor
```

### Test RTSP
```bash
# VLC (command line)
vlc --rtsp-tcp rtsp://192.168.1.XXX:8554/mjpeg/1

# FFplay (low latency)
ffplay -rtsp_transport tcp -fflags nobuffer -flags low_delay \
  rtsp://192.168.1.XXX:8554/mjpeg/1

# Test connection
telnet 192.168.1.XXX 8554
```

### Test HTTP
```bash
# Status
curl http://192.168.1.XXX/status | jq

# All resolutions
for i in {0..6}; do
  curl "http://192.168.1.XXX/set_resolution?value=$i"
  sleep 3
done

# Flash blink
curl "http://192.168.1.XXX/set_flash?value=255"
sleep 1
curl "http://192.168.1.XXX/set_flash?value=0"
```

---

## 🐛 Quick Troubleshooting

### ❌ Camera Init Failed
```
Error: 0x105
Fix: Check camera cable, power supply (5V 2A min)
```

### ❌ WiFi Won't Connect
```
Fix: 
- Check SSID/password (case-sensitive)
- Ensure 2.4GHz WiFi (not 5GHz)
- Move closer to router
```

### ❌ RTSP Won't Connect
```
Fix:
- Must use --rtsp-tcp flag
- Check firewall/port 8554
- Try: telnet IP 8554
```

### ❌ Frames Corrupted
```
Fix:
- Lower resolution to QVGA
- Better power supply
- Reduce quality value (e.g., 10)
```

### ❌ ESP32 Keeps Crashing
```
Fix:
- Check Serial Monitor for stack overflow
- Increase task stack size (8192→16384)
- Verify power supply quality
```

---

## 📊 Recommended Settings

### Low Latency (Real-time)
```
Resolution: QVGA (6)
Quality:    12
Frame Rate: 20 FPS
Bandwidth:  ~300 KB/s
```

### Balanced
```
Resolution: VGA (4)
Quality:    15
Frame Rate: 15 FPS
Bandwidth:  ~600 KB/s
```

### High Quality
```
Resolution: XGA (2)
Quality:    10
Frame Rate: 10 FPS
Bandwidth:  ~1 MB/s
```

### Low Bandwidth
```
Resolution: CIF (5)
Quality:    25
Frame Rate: 15 FPS
Bandwidth:  ~150 KB/s
```

---

## 🔒 Security Checklist

- [ ] Change WiFi credentials
- [ ] Add HTTP authentication (see API_EXAMPLES.md)
- [ ] Use firewall to restrict access
- [ ] Consider VPN for remote access
- [ ] Don't expose to public internet without auth
- [ ] Use static IP in router
- [ ] Enable WPA2/WPA3 on WiFi

---

## 📁 Project Structure

```
Simple_RTSP_ESP32CAM/
├── Simple_RTSP_ESP32CAM.ino  # Main firmware
├── platformio.ini             # PlatformIO config
├── README.md                  # Documentation
├── ARCHITECTURE.md            # System design
├── TROUBLESHOOTING.md         # Debug guide
├── API_EXAMPLES.md            # Integration examples
├── QUICK_REFERENCE.md         # This file
└── src/
    ├── OV2640.cpp/h          # Camera driver
    ├── CRtspSession.cpp/h    # RTSP session
    ├── CStreamer.cpp/h       # Base streamer
    └── OV2640Streamer.cpp/h  # Camera streamer
```

---

## 🎯 Performance Tips

### Increase FPS
```cpp
// In rtspTask()
uint32_t msecPerFrame = 33;  // 30 FPS (was 50 = 20 FPS)
```

### Reduce Latency
```cpp
// Lower resolution
cameraSettings.resolution = FRAMESIZE_QVGA;

// Disable WiFi power save
WiFi.setSleep(false);

// Increase RTSP priority
xTaskCreatePinnedToCore(rtspTask, "rtsp", 8192, NULL, 3, NULL, 0);
//                                                      ^ was 2
```

### Save Power
```cpp
// Lower frame rate
uint32_t msecPerFrame = 100;  // 10 FPS

// Enable WiFi sleep
WiFi.setSleep(true);

// Turn off flash when not needed
analogWrite(FLASH_LED_PIN, 0);
```

---

## 📞 Support Resources

| Resource | Link |
|----------|------|
| **README** | Full documentation |
| **ARCHITECTURE** | System design & diagrams |
| **TROUBLESHOOTING** | Detailed error solutions |
| **API_EXAMPLES** | Integration code samples |
| **Serial Monitor** | Real-time debug output |
| **GitHub Issues** | Community support |

---

## 🎓 Learning Resources

### Understanding RTSP
- RTSP Protocol: RFC 2326
- RTP/JPEG: RFC 2435
- Test with Wireshark: `tcp.port == 8554`

### Understanding FreeRTOS
- Tasks: Concurrent execution
- Mutex: Thread synchronization
- Core Pinning: CPU affinity
- Priority: Scheduling order

### ESP32-CAM Resources
- [ESP32 Camera Docs](https://github.com/espressif/esp32-camera)
- [Micro-RTSP Library](https://github.com/geeksville/Micro-RTSP)
- [FreeRTOS Guide](https://www.freertos.org/Documentation)

---

## ⌨️ Keyboard Shortcuts (Serial Monitor)

| Key | Action |
|-----|--------|
| `Ctrl+L` | Clear screen |
| `Ctrl+T` | Show timestamp |
| `Ctrl+C` | Stop/interrupt |
| `Ctrl+]` | Exit monitor |

---

## 📈 Monitoring Commands

### System Info
```cpp
ESP.getChipModel();        // ESP32
ESP.getCpuFreqMHz();       // 240
ESP.getFreeHeap();         // Free memory
ESP.getPsramSize();        // PSRAM size
```

### Task Info
```cpp
uxTaskGetStackHighWaterMark(NULL);  // Stack usage
xPortGetCoreID();                   // Current core
vTaskList();                        // All tasks
```

### Network Info
```cpp
WiFi.localIP();     // IP address
WiFi.RSSI();        // Signal strength
WiFi.channel();     // WiFi channel
WiFi.macAddress();  // MAC address
```

---

## 🎬 Quick Start Example

```bash
# 1. Edit WiFi credentials in .ino file

# 2. Upload
pio run -t upload

# 3. Monitor
pio device monitor

# 4. Note IP address (e.g., 192.168.1.100)

# 5. Test RTSP
ffplay -rtsp_transport tcp rtsp://192.168.1.100:8554/mjpeg/1

# 6. Open dashboard
firefox http://192.168.1.100/

# 7. Done! 🎉
```

---

**Keep this card handy for quick reference!** 📋✨
