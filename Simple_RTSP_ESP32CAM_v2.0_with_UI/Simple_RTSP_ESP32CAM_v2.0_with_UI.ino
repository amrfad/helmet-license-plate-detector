/*
 * ESP32-CAM Dual-Core RTSP Server + HTTP Dashboard
 * 
 * Arsitektur:
 * - Core 0: RTSP Server (real-time streaming)
 * - Core 1: HTTP Web Dashboard (konfigurasi)
 * 
 * Fitur:
 * - RTSP streaming stabil dengan mutex protection
 * - HTTP Dashboard untuk konfigurasi resolusi, quality, LED flash
 * - JSON API untuk monitoring status
 * - Safe camera reconfiguration tanpa corrupt stream
 * 
 * Cara menggunakan:
 * 1. Sesuaikan SSID dan Password WiFi
 * 2. Upload ke ESP32-CAM
 * 3. RTSP URL: rtsp://IP_ADDRESS:8554/mjpeg/1
 * 4. HTTP Dashboard: http://IP_ADDRESS/
 * 5. JSON Status: http://IP_ADDRESS/status
 */

#include "src/OV2640.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include "src/OV2640Streamer.h"
#include "src/CRtspSession.h"

// ===== SETTING WIFI =====
const char* ssid = "Pondok Polban 19A";           // Ganti dengan nama WiFi Anda
const char* password = "fajar123";    // Ganti dengan password WiFi Anda

// ===== SETTING RTSP =====
#define RTSP_PORT 8554
#define HTTP_PORT 80

// ===== LED Flash Pin (AI Thinker) =====
#define FLASH_LED_PIN 4

// ===== Global Objects =====
OV2640 cam;
WiFiServer rtspServer(RTSP_PORT);
WebServer webServer(HTTP_PORT);
CStreamer *streamer;

// ===== Mutex untuk Camera Access =====
SemaphoreHandle_t cameraMutex;

// ===== Camera Settings (Shared between cores) =====
struct CameraSettings {
    framesize_t resolution = FRAMESIZE_QVGA;  // Default QVGA
    int jpegQuality = 12;                      // Default 12 (lower = better quality)
    int flashIntensity = 0;                    // 0-255
    bool rtspRunning = false;
} cameraSettings;

// ===== Task Handles =====
TaskHandle_t rtspTaskHandle = NULL;
TaskHandle_t webTaskHandle = NULL;

// ===== Forward Declarations =====
void rtspTask(void* parameter);
void webTask(void* parameter);
void setupWebServer();
void applyCameraSettings();
void restartRTSP();
void handleRoot();
void handleStatus();
void handleSetResolution();
void handleSetQuality();
void handleSetFlash();


void setup() 
{
    Serial.begin(115200);
    Serial.println("\n\n=================================");
    Serial.println("ESP32-CAM Dual-Core RTSP + HTTP");
    Serial.println("=================================\n");

    // Inisialisasi LED Flash
    pinMode(FLASH_LED_PIN, OUTPUT);
    digitalWrite(FLASH_LED_PIN, LOW);

    // Buat Mutex untuk Camera Access
    cameraMutex = xSemaphoreCreateMutex();
    if (cameraMutex == NULL) {
        Serial.println("GAGAL membuat mutex!");
        return;
    }
    Serial.println("Mutex berhasil dibuat");

    // Inisialisasi kamera dengan konfigurasi AI Thinker
    Serial.println("Menginisialisasi kamera...");
    esp_err_t err = cam.init(esp32cam_aithinker_config);
    
    if (err != ESP_OK) {
        Serial.printf("Gagal menginisialisasi kamera! Error: 0x%x\n", err);
        return;
    }
    
    // Set konfigurasi default kamera
    sensor_t * s = esp_camera_sensor_get();
    if (s != NULL) {
        s->set_framesize(s, cameraSettings.resolution);
        s->set_quality(s, cameraSettings.jpegQuality);
    }
    
    Serial.println("Kamera berhasil diinisialisasi!");
    Serial.printf("Resolusi: QVGA, Quality: %d\n", cameraSettings.jpegQuality);

    // Koneksi ke WiFi
    Serial.printf("\nMenghubungkan ke WiFi: %s ", ssid);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println(" TERHUBUNG!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal Strength (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

    // Setup Web Server
    setupWebServer();
    
    Serial.println("\n=================================");
    Serial.println("SISTEM SIAP!");
    Serial.println("=================================");
    Serial.printf("RTSP URL: rtsp://%s:%d/mjpeg/1\n", WiFi.localIP().toString().c_str(), RTSP_PORT);
    Serial.printf("HTTP Dashboard: http://%s/\n", WiFi.localIP().toString().c_str());
    Serial.printf("JSON Status: http://%s/status\n", WiFi.localIP().toString().c_str());
    Serial.println("=================================\n");

    // Buat RTSP Task pada Core 0 (Real-time Priority)
    xTaskCreatePinnedToCore(
        rtspTask,           // Function
        "rtsp",             // Name
        8192,               // Stack size (increased for stability)
        NULL,               // Parameter
        2,                  // Priority (higher for real-time)
        &rtspTaskHandle,    // Task handle
        0                   // Core 0
    );
    Serial.println("RTSP Task dimulai di Core 0");

    // Buat Web Task pada Core 1
    xTaskCreatePinnedToCore(
        webTask,            // Function
        "web",              // Name
        8192,               // Stack size
        NULL,               // Parameter
        1,                  // Priority (lower than RTSP)
        &webTaskHandle,     // Task handle
        1                   // Core 1
    );
    Serial.println("Web Task dimulai di Core 1");
}

void loop() 
{
    // Loop kosong karena semua logic ada di tasks
    vTaskDelay(1000 / portTICK_PERIOD_MS);
}

// ===== RTSP TASK (Core 0 - Real-time) =====
void rtspTask(void* parameter) 
{
    Serial.println("[RTSP Task] Memulai RTSP Server...");
    
    // Mulai RTSP Server
    rtspServer.begin();
    
    // Buat streamer untuk RTSP dengan mutex protection
    if (xSemaphoreTake(cameraMutex, portMAX_DELAY) == pdTRUE) {
        streamer = new OV2640Streamer(&cam);
        cameraSettings.rtspRunning = true;
        xSemaphoreGive(cameraMutex);
    }
    
    Serial.println("[RTSP Task] RTSP Server aktif di Core 0");
    
    uint32_t msecPerFrame = 50;  // 20 FPS
    uint32_t lastimage = millis();
    
    for(;;) {
        // Handle request dari client yang sudah terhubung
        if (cameraSettings.rtspRunning && streamer != NULL) {
            streamer->handleRequests(0);
            
            // Broadcast frame baru dengan mutex protection
            uint32_t now = millis();
            if (streamer->anySessions()) {
                if (now > lastimage + msecPerFrame || now < lastimage) {
                    if (xSemaphoreTake(cameraMutex, 10 / portTICK_PERIOD_MS) == pdTRUE) {
                        streamer->streamImage(now);
                        xSemaphoreGive(cameraMutex);
                    }
                    lastimage = now;
                }
            }
        }
        
        // Terima koneksi client baru
        WiFiClient rtspClient = rtspServer.accept();
        if (rtspClient) {
            Serial.print("[RTSP Task] Client baru: ");
            Serial.println(rtspClient.remoteIP());
            
            if (cameraSettings.rtspRunning && streamer != NULL) {
                WiFiClient* client = new WiFiClient(rtspClient);
                streamer->addSession(client);
            }
        }
        
        // Yield untuk task lain
        vTaskDelay(1 / portTICK_PERIOD_MS);
    }
}

// ===== WEB TASK (Core 1) =====
void webTask(void* parameter) 
{
    Serial.println("[Web Task] Memulai HTTP Server...");
    webServer.begin();
    Serial.println("[Web Task] HTTP Server aktif di Core 1");
    
    for(;;) {
        webServer.handleClient();
        vTaskDelay(10 / portTICK_PERIOD_MS); // 10ms delay untuk efisiensi
    }
}

// ===== SETUP WEB SERVER =====
void setupWebServer() 
{
    webServer.on("/", handleRoot);
    webServer.on("/status", handleStatus);
    webServer.on("/set_resolution", handleSetResolution);
    webServer.on("/set_quality", handleSetQuality);
    webServer.on("/set_flash", handleSetFlash);
}

// ===== HTTP HANDLERS =====
void handleRoot() 
{
    String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32-CAM Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f0f0f0; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        h2 { color: #666; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        label { display: block; margin: 10px 0 5px; font-weight: bold; color: #555; }
        select, input[type="number"], input[type="range"] { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; margin-top: 10px; font-size: 16px; }
        button:hover { background: #45a049; }
        .status { background: #e7f3ff; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .value { color: #2196F3; font-weight: bold; }
        .range-container { display: flex; align-items: center; gap: 10px; }
        .range-value { min-width: 40px; text-align: right; font-weight: bold; color: #4CAF50; }
    </style>
</head>
<body>
    <h1>🎥 ESP32-CAM Dashboard</h1>
    
    <div class="card">
        <h2>📊 Status Saat Ini</h2>
        <div class="status">
            <div>Resolusi: <span class="value" id="currentRes">Loading...</span></div>
            <div>JPEG Quality: <span class="value" id="currentQuality">Loading...</span></div>
            <div>Flash Intensity: <span class="value" id="currentFlash">Loading...</span></div>
            <div>RTSP Status: <span class="value" id="rtspStatus">Loading...</span></div>
        </div>
        <button onclick="updateStatus()">Refresh Status</button>
    </div>
    
    <div class="card">
        <h2>🖼️ Pengaturan Resolusi</h2>
        <label>Pilih Resolusi:</label>
        <select id="resolution">
            <option value="0">UXGA (1600x1200)</option>
            <option value="1">SXGA (1280x1024)</option>
            <option value="2">XGA (1024x768)</option>
            <option value="3">SVGA (800x600)</option>
            <option value="4">VGA (640x480)</option>
            <option value="5">CIF (400x296)</option>
            <option value="6" selected>QVGA (320x240)</option>
        </select>
        <button onclick="setResolution()">Terapkan Resolusi</button>
    </div>
    
    <div class="card">
        <h2>⚙️ Pengaturan JPEG Quality</h2>
        <label>Quality (10-63, lower = better):</label>
        <div class="range-container">
            <input type="range" id="quality" min="10" max="63" value="12" oninput="document.getElementById('qualityValue').innerText = this.value">
            <span class="range-value" id="qualityValue">12</span>
        </div>
        <button onclick="setQuality()">Terapkan Quality</button>
    </div>
    
    <div class="card">
        <h2>💡 Kontrol LED Flash</h2>
        <label>Flash Intensity (0-255):</label>
        <div class="range-container">
            <input type="range" id="flash" min="0" max="255" value="0" oninput="document.getElementById('flashValue').innerText = this.value">
            <span class="range-value" id="flashValue">0</span>
        </div>
        <button onclick="setFlash()">Terapkan Flash</button>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('currentRes').innerText = getResolutionName(data.resolution);
                    document.getElementById('currentQuality').innerText = data.quality;
                    document.getElementById('currentFlash').innerText = data.flash;
                    document.getElementById('rtspStatus').innerText = data.rtsp_running ? '✅ Running' : '❌ Stopped';
                });
        }
        
        function getResolutionName(val) {
            const names = ['UXGA', 'SXGA', 'XGA', 'SVGA', 'VGA', 'CIF', 'QVGA'];
            return names[val] || 'Unknown';
        }
        
        function setResolution() {
            const res = document.getElementById('resolution').value;
            fetch('/set_resolution?value=' + res)
                .then(response => response.text())
                .then(data => { alert(data); updateStatus(); });
        }
        
        function setQuality() {
            const q = document.getElementById('quality').value;
            fetch('/set_quality?value=' + q)
                .then(response => response.text())
                .then(data => { alert(data); updateStatus(); });
        }
        
        function setFlash() {
            const f = document.getElementById('flash').value;
            fetch('/set_flash?value=' + f)
                .then(response => response.text())
                .then(data => { alert(data); updateStatus(); });
        }
        
        // Auto-update status setiap 5 detik
        setInterval(updateStatus, 5000);
        updateStatus();
    </script>
</body>
</html>
)rawliteral";
    
    webServer.send(200, "text/html", html);
}

void handleStatus() 
{
    String json = "{";
    json += "\"resolution\":" + String((int)cameraSettings.resolution) + ",";
    json += "\"quality\":" + String(cameraSettings.jpegQuality) + ",";
    json += "\"flash\":" + String(cameraSettings.flashIntensity) + ",";
    json += "\"rtsp_running\":" + String(cameraSettings.rtspRunning ? "true" : "false");
    json += "}";
    
    webServer.send(200, "application/json", json);
}

void handleSetResolution() 
{
    if (webServer.hasArg("value")) {
        int resVal = webServer.arg("value").toInt();
        
        // Mapping value ke framesize_t
        framesize_t newRes = FRAMESIZE_QVGA;
        switch(resVal) {
            case 0: newRes = FRAMESIZE_UXGA; break;
            case 1: newRes = FRAMESIZE_SXGA; break;
            case 2: newRes = FRAMESIZE_XGA; break;
            case 3: newRes = FRAMESIZE_SVGA; break;
            case 4: newRes = FRAMESIZE_VGA; break;
            case 5: newRes = FRAMESIZE_CIF; break;
            case 6: newRes = FRAMESIZE_QVGA; break;
            default: newRes = FRAMESIZE_QVGA; break;
        }
        
        cameraSettings.resolution = newRes;
        restartRTSP();
        
        webServer.send(200, "text/plain", "Resolusi berhasil diubah! RTSP di-restart.");
        Serial.printf("[HTTP] Resolusi diubah ke: %d\n", resVal);
    } else {
        webServer.send(400, "text/plain", "Parameter 'value' tidak ditemukan!");
    }
}

void handleSetQuality() 
{
    if (webServer.hasArg("value")) {
        int quality = webServer.arg("value").toInt();
        
        if (quality >= 10 && quality <= 63) {
            cameraSettings.jpegQuality = quality;
            restartRTSP();
            
            webServer.send(200, "text/plain", "Quality berhasil diubah! RTSP di-restart.");
            Serial.printf("[HTTP] Quality diubah ke: %d\n", quality);
        } else {
            webServer.send(400, "text/plain", "Quality harus antara 10-63!");
        }
    } else {
        webServer.send(400, "text/plain", "Parameter 'value' tidak ditemukan!");
    }
}

void handleSetFlash() 
{
    if (webServer.hasArg("value")) {
        int intensity = webServer.arg("value").toInt();
        
        if (intensity >= 0 && intensity <= 255) {
            cameraSettings.flashIntensity = intensity;
            analogWrite(FLASH_LED_PIN, intensity);
            
            webServer.send(200, "text/plain", "Flash intensity berhasil diubah!");
            Serial.printf("[HTTP] Flash intensity: %d\n", intensity);
        } else {
            webServer.send(400, "text/plain", "Intensity harus antara 0-255!");
        }
    } else {
        webServer.send(400, "text/plain", "Parameter 'value' tidak ditemukan!");
    }
}

// ===== SAFE RTSP RESTART =====
void restartRTSP() 
{
    Serial.println("[RTSP] Memulai restart...");
    
    // Step 1: Tandai RTSP untuk berhenti
    cameraSettings.rtspRunning = false;
    vTaskDelay(100 / portTICK_PERIOD_MS); // Tunggu task RTSP berhenti streaming
    
    // Step 2: Ambil mutex dan hapus streamer
    if (xSemaphoreTake(cameraMutex, portMAX_DELAY) == pdTRUE) {
        if (streamer != NULL) {
            delete streamer;
            streamer = NULL;
            Serial.println("[RTSP] Streamer dihapus");
        }
        
        // Step 3: Apply camera settings
        sensor_t * s = esp_camera_sensor_get();
        if (s != NULL) {
            s->set_framesize(s, cameraSettings.resolution);
            s->set_quality(s, cameraSettings.jpegQuality);
            Serial.printf("[RTSP] Settings diterapkan - Res: %d, Q: %d\n", 
                         cameraSettings.resolution, cameraSettings.jpegQuality);
        }
        
        // Step 4: Buat streamer baru
        streamer = new OV2640Streamer(&cam);
        cameraSettings.rtspRunning = true;
        Serial.println("[RTSP] Streamer baru dibuat");
        
        xSemaphoreGive(cameraMutex);
    }
    
    Serial.println("[RTSP] Restart selesai!");
}
