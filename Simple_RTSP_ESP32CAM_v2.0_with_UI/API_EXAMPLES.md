# API Examples & Integration Guide

## 🌐 HTTP API Reference

Base URL: `http://<ESP32_IP_ADDRESS>/`

### Authentication
Currently **no authentication** required. See Security section for recommendations.

---

## 📡 Endpoints

### 1. GET /status

Get current camera configuration and RTSP status.

**Request:**
```bash
curl http://192.168.1.100/status
```

**Response (200 OK):**
```json
{
  "resolution": 6,
  "quality": 12,
  "flash": 0,
  "rtsp_running": true
}
```

**Resolution Mapping:**
| Value | Resolution | Dimensions |
|-------|-----------|-----------|
| 0 | UXGA | 1600x1200 |
| 1 | SXGA | 1280x1024 |
| 2 | XGA | 1024x768 |
| 3 | SVGA | 800x600 |
| 4 | VGA | 640x480 |
| 5 | CIF | 400x296 |
| 6 | QVGA | 320x240 |

**Example Response Handler:**
```javascript
fetch('http://192.168.1.100/status')
  .then(response => response.json())
  .then(data => {
    console.log('Current resolution:', data.resolution);
    console.log('JPEG quality:', data.quality);
    console.log('Flash intensity:', data.flash);
    console.log('RTSP running:', data.rtsp_running);
  });
```

---

### 2. GET /set_resolution?value=X

Change camera resolution (requires RTSP restart).

**Parameters:**
- `value` (required): Integer 0-6

**Request:**
```bash
curl "http://192.168.1.100/set_resolution?value=4"
```

**Response (200 OK):**
```
Resolusi berhasil diubah! RTSP di-restart.
```

**Response (400 Bad Request):**
```
Parameter 'value' tidak ditemukan!
```

**Side Effects:**
- RTSP server will restart (all clients disconnected)
- Frame rate may change based on resolution
- Takes ~1-2 seconds to complete

**Example:**
```python
import requests

def set_resolution(ip, resolution):
    """
    Set camera resolution
    resolution: 0=UXGA, 1=SXGA, 2=XGA, 3=SVGA, 4=VGA, 5=CIF, 6=QVGA
    """
    url = f"http://{ip}/set_resolution?value={resolution}"
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"Resolution changed to {resolution}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

# Usage
set_resolution("192.168.1.100", 4)  # Set to VGA
```

---

### 3. GET /set_quality?value=X

Change JPEG quality (requires RTSP restart).

**Parameters:**
- `value` (required): Integer 10-63 (lower = better quality, larger file)

**Request:**
```bash
curl "http://192.168.1.100/set_quality?value=10"
```

**Response (200 OK):**
```
Quality berhasil diubah! RTSP di-restart.
```

**Response (400 Bad Request):**
```
Quality harus antara 10-63!
```

**Quality Guidelines:**
| Quality | Use Case | File Size |
|---------|----------|----------|
| 10-15 | High quality | Large |
| 16-20 | Balanced | Medium |
| 21-30 | Low bandwidth | Small |
| 31-63 | Not recommended | Very small |

**Example:**
```javascript
async function setQuality(ip, quality) {
    const response = await fetch(`http://${ip}/set_quality?value=${quality}`);
    const text = await response.text();
    
    if (response.ok) {
        console.log('Quality updated:', text);
    } else {
        console.error('Failed:', text);
    }
}

// Usage
setQuality('192.168.1.100', 12);
```

---

### 4. GET /set_flash?value=X

Control LED flash intensity (no restart required).

**Parameters:**
- `value` (required): Integer 0-255 (0=off, 255=max brightness)

**Request:**
```bash
curl "http://192.168.1.100/set_flash?value=128"
```

**Response (200 OK):**
```
Flash intensity berhasil diubah!
```

**Response (400 Bad Request):**
```
Intensity harus antara 0-255!
```

**Example:**
```bash
# Turn on flash at 50% brightness
curl "http://192.168.1.100/set_flash?value=128"

# Turn off flash
curl "http://192.168.1.100/set_flash?value=0"

# Maximum brightness
curl "http://192.168.1.100/set_flash?value=255"
```

**Python Example:**
```python
def set_flash(ip, intensity):
    """Control LED flash (0-255)"""
    if not 0 <= intensity <= 255:
        print("Intensity must be 0-255")
        return False
    
    url = f"http://{ip}/set_flash?value={intensity}"
    response = requests.get(url)
    return response.status_code == 200

# Turn on at 75%
set_flash("192.168.1.100", 192)
```

---

### 5. GET / (Root)

HTML dashboard for manual configuration.

**Request:**
```bash
curl http://192.168.1.100/
```

**Response:**
Returns full HTML dashboard (see browser for UI).

---

## 🔌 Integration Examples

### Python Integration

```python
import requests
import time

class ESP32Camera:
    def __init__(self, ip):
        self.ip = ip
        self.base_url = f"http://{ip}"
    
    def get_status(self):
        """Get current camera status"""
        response = requests.get(f"{self.base_url}/status")
        return response.json()
    
    def set_resolution(self, resolution):
        """Set resolution (0-6)"""
        response = requests.get(
            f"{self.base_url}/set_resolution",
            params={'value': resolution}
        )
        return response.status_code == 200
    
    def set_quality(self, quality):
        """Set JPEG quality (10-63)"""
        response = requests.get(
            f"{self.base_url}/set_quality",
            params={'value': quality}
        )
        return response.status_code == 200
    
    def set_flash(self, intensity):
        """Set flash intensity (0-255)"""
        response = requests.get(
            f"{self.base_url}/set_flash",
            params={'value': intensity}
        )
        return response.status_code == 200
    
    def wait_for_restart(self, timeout=10):
        """Wait for RTSP to restart after config change"""
        time.sleep(2)  # Initial delay
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                status = self.get_status()
                if status['rtsp_running']:
                    return True
            except:
                pass
            time.sleep(0.5)
        
        return False

# Usage example
camera = ESP32Camera("192.168.1.100")

# Get current status
status = camera.get_status()
print(f"Current resolution: {status['resolution']}")
print(f"RTSP running: {status['rtsp_running']}")

# Change to VGA resolution
print("Changing to VGA...")
camera.set_resolution(4)
camera.wait_for_restart()
print("Resolution changed!")

# Adjust quality
camera.set_quality(15)
camera.wait_for_restart()

# Turn on flash
camera.set_flash(128)
```

---

### Node.js Integration

```javascript
const axios = require('axios');

class ESP32Camera {
    constructor(ip) {
        this.baseURL = `http://${ip}`;
    }
    
    async getStatus() {
        const response = await axios.get(`${this.baseURL}/status`);
        return response.data;
    }
    
    async setResolution(resolution) {
        const response = await axios.get(`${this.baseURL}/set_resolution`, {
            params: { value: resolution }
        });
        return response.status === 200;
    }
    
    async setQuality(quality) {
        const response = await axios.get(`${this.baseURL}/set_quality`, {
            params: { value: quality }
        });
        return response.status === 200;
    }
    
    async setFlash(intensity) {
        const response = await axios.get(`${this.baseURL}/set_flash`, {
            params: { value: intensity }
        });
        return response.status === 200;
    }
    
    async waitForRestart(timeout = 10000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            try {
                const status = await this.getStatus();
                if (status.rtsp_running) {
                    return true;
                }
            } catch (err) {
                // Ignore errors during restart
            }
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        return false;
    }
}

// Usage
(async () => {
    const camera = new ESP32Camera('192.168.1.100');
    
    // Get status
    const status = await camera.getStatus();
    console.log('Current status:', status);
    
    // Change resolution to SVGA
    await camera.setResolution(3);
    await camera.waitForRestart();
    console.log('Resolution changed!');
    
    // Flash control
    await camera.setFlash(200);
    console.log('Flash on');
})();
```

---

### Bash Script Integration

```bash
#!/bin/bash

ESP32_IP="192.168.1.100"

# Function to get status
get_status() {
    curl -s "http://${ESP32_IP}/status" | jq '.'
}

# Function to set resolution
set_resolution() {
    local res=$1
    curl -s "http://${ESP32_IP}/set_resolution?value=${res}"
    sleep 2  # Wait for restart
}

# Function to set quality
set_quality() {
    local quality=$1
    curl -s "http://${ESP32_IP}/set_quality?value=${quality}"
    sleep 2
}

# Function to set flash
set_flash() {
    local intensity=$1
    curl -s "http://${ESP32_IP}/set_flash?value=${intensity}"
}

# Main script
echo "ESP32-CAM Controller"
echo "===================="

# Show current status
echo -e "\nCurrent Status:"
get_status

# Change to QVGA for low latency
echo -e "\nSetting QVGA resolution..."
set_resolution 6

# Set high quality
echo -e "\nSetting quality to 10..."
set_quality 10

# Turn on flash at 50%
echo -e "\nTurning on flash..."
set_flash 128

# Show updated status
echo -e "\nUpdated Status:"
get_status
```

---

### Home Assistant Integration

```yaml
# configuration.yaml
rest_command:
  esp32cam_set_resolution:
    url: "http://192.168.1.100/set_resolution?value={{ value }}"
    method: GET
  
  esp32cam_set_quality:
    url: "http://192.168.1.100/set_quality?value={{ value }}"
    method: GET
  
  esp32cam_set_flash:
    url: "http://192.168.1.100/set_flash?value={{ value }}"
    method: GET

sensor:
  - platform: rest
    name: ESP32-CAM Status
    resource: http://192.168.1.100/status
    json_attributes:
      - resolution
      - quality
      - flash
      - rtsp_running
    value_template: '{{ value_json.rtsp_running }}'

light:
  - platform: template
    lights:
      esp32cam_flash:
        friendly_name: "ESP32-CAM Flash"
        turn_on:
          service: rest_command.esp32cam_set_flash
          data:
            value: 255
        turn_off:
          service: rest_command.esp32cam_set_flash
          data:
            value: 0
        set_level:
          service: rest_command.esp32cam_set_flash
          data_template:
            value: "{{ brightness }}"

# Automation example
automation:
  - alias: "ESP32-CAM Night Mode"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: rest_command.esp32cam_set_flash
        data:
          value: 128
      - service: rest_command.esp32cam_set_resolution
        data:
          value: 6  # QVGA for better low-light performance
```

---

### MQTT Bridge (Advanced)

```python
import paho.mqtt.client as mqtt
import requests
import json
import time

class ESP32CameraMQTTBridge:
    def __init__(self, esp32_ip, mqtt_broker):
        self.esp32_ip = esp32_ip
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(mqtt_broker, 1883, 60)
    
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker")
        client.subscribe("esp32cam/set/#")
        client.subscribe("esp32cam/get/status")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        if topic == "esp32cam/set/resolution":
            self.set_resolution(int(payload))
        elif topic == "esp32cam/set/quality":
            self.set_quality(int(payload))
        elif topic == "esp32cam/set/flash":
            self.set_flash(int(payload))
        elif topic == "esp32cam/get/status":
            self.publish_status()
    
    def set_resolution(self, value):
        url = f"http://{self.esp32_ip}/set_resolution?value={value}"
        requests.get(url)
        time.sleep(2)
        self.publish_status()
    
    def set_quality(self, value):
        url = f"http://{self.esp32_ip}/set_quality?value={value}"
        requests.get(url)
        time.sleep(2)
        self.publish_status()
    
    def set_flash(self, value):
        url = f"http://{self.esp32_ip}/set_flash?value={value}"
        requests.get(url)
    
    def publish_status(self):
        response = requests.get(f"http://{self.esp32_ip}/status")
        status = response.json()
        self.mqtt_client.publish("esp32cam/status", json.dumps(status))
    
    def run(self):
        self.mqtt_client.loop_forever()

# Usage
bridge = ESP32CameraMQTTBridge("192.168.1.100", "mqtt.local")
bridge.run()
```

---

## 🔒 Security Recommendations

### Add HTTP Basic Auth

```cpp
// Add to .ino file
#include <WebServer.h>

const char* http_username = "admin";
const char* http_password = "your_password";

void handleRoot() {
    if (!webServer.authenticate(http_username, http_password)) {
        return webServer.requestAuthentication();
    }
    
    // ... existing code ...
}

// Apply to all handlers
void setupWebServer() {
    webServer.on("/", handleRoot);
    webServer.on("/status", handleAuthenticatedStatus);
    // ... etc
}
```

### Rate Limiting

```cpp
// Prevent spam requests
unsigned long lastRequestTime = 0;
const unsigned long REQUEST_COOLDOWN = 1000; // 1 second

void handleSetResolution() {
    unsigned long now = millis();
    if (now - lastRequestTime < REQUEST_COOLDOWN) {
        webServer.send(429, "text/plain", "Too many requests");
        return;
    }
    lastRequestTime = now;
    
    // ... existing code ...
}
```

---

## 📊 Monitoring & Logging

### Log All API Calls

```python
import requests
from datetime import datetime

class LoggedESP32Camera(ESP32Camera):
    def __init__(self, ip, log_file="camera.log"):
        super().__init__(ip)
        self.log_file = log_file
    
    def log(self, action, result):
        timestamp = datetime.now().isoformat()
        with open(self.log_file, 'a') as f:
            f.write(f"{timestamp} - {action}: {result}\n")
    
    def set_resolution(self, resolution):
        result = super().set_resolution(resolution)
        self.log(f"set_resolution({resolution})", "OK" if result else "FAIL")
        return result

# Usage
camera = LoggedESP32Camera("192.168.1.100")
camera.set_resolution(4)  # Logged automatically
```

---

**Happy Integrating! 🚀**
