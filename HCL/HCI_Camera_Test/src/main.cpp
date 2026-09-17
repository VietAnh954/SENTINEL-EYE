// ============================================================
// SENTINEL EYE - ESP32-CAM Firmware
// Chức năng: MJPEG Stream + Buzzer Control qua HTTP
// ============================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "soc/soc.h"           // Thêm thư viện chống sụt áp
#include "soc/rtc_cntl_reg.h"  // Thêm thư viện chống sụt áp

// ===================== CẤU HÌNH PHẦN CỨNG =====================
// Chân camera AI-Thinker ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Chân Buzzer (Active Buzzer nối vào GPIO 14 và GND)
#define BUZZER_PIN        14

// ===================== CẤU HÌNH WIFI =====================
// ĐIỀN TÊN VÀ MẬT KHẨU WIFI NHÀ BẠN VÀO ĐÂY
const char* ssid = "Cafe Ba Nam";
const char* password = "715taquangbuu";
// ===========================================================

// Web server chạy trên port 80
WebServer server(80);
WiFiServer controlServer(81); // Thêm phân luồng Port 81 chuyên trách nhận lệnh hú còi khẩn cấp

// Prototype khai báo hàm trước cho C++ để tránh "was not declared in this scope"
void processBuzzerControl();

// Biến trạng thái buzzer
bool buzzerActive = false;

// ===================== KHỞI TẠO CAMERA =====================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  
  // Trả lại tần số chuẩn 20MHz cho OV2640
  config.xclk_freq_hz = 10000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Cấu hình chất lượng dựa trên PSRAM
  if (psramFound()) {
    Serial.println("PSRAM found! Sử dụng VGA 640x480");
    config.frame_size = FRAMESIZE_VGA;    // 640x480 - đủ tốt cho YOLO detect
    config.jpeg_quality = 12;              // Chất lượng tốt (1-63, số nhỏ = chất lượng cao)
    config.fb_count = 2;                   // Double buffer cho stream mượt
  } else {
    Serial.println("Không có PSRAM. Sử dụng HVGA để tránh tràn RAM");
    config.frame_size = FRAMESIZE_HVGA;  
    config.jpeg_quality = 20;
    config.fb_count = 1;
  }

  // Khởi động cứng (Hard Reset) mạch nguồn của OV2640 trước khi init
  Serial.println("Dang khoi dong cung (Hard-Reset) camera OV2640...");
  pinMode(PWDN_GPIO_NUM, OUTPUT);
  digitalWrite(PWDN_GPIO_NUM, HIGH); // Tắt nguồn camera OV2640
  delay(100);
  digitalWrite(PWDN_GPIO_NUM, LOW);  // Bật nguồn camera OV2640
  delay(100);

  esp_err_t err = esp_camera_init(&config);
  
  if (err == 0x106) {
    Serial.println("Cảnh báo [0x106]: Camera của bạn KHÔNG hỗ trợ nén JPEG bằng phần cứng!");
    Serial.println("Đang tự động chuyển sang chế độ RGB565 và nén JPEG bằng phần mềm (Software JPEG)...");
    
    // Đổi sang RGB565 và giới hạn độ phân giải để tránh tràn RAM
    config.pixel_format = PIXFORMAT_RGB565;
    // Đã đổi thành QVGA (320x240) để lấy lại toàn bộ GÓC RỘNG BAO QUÁT (Full FOV).
    config.frame_size = FRAMESIZE_QVGA; 
    config.fb_count = 2; // Bật lại hệ thống Double-Buffer (nhờ có Mạch PSRAM) để stream gối đầu liên tục không nghỉ
    
    err = esp_camera_init(&config);
  }

  if (err != ESP_OK) {
    Serial.printf("Lỗi khởi động camera: 0x%x\n", err);
    return false;
  }

  // Tinh chỉnh sensor cho hình ảnh tốt hơn
  sensor_t * s = esp_camera_sensor_get();
  if (s) {
    Serial.printf(">> Đã nhận dạng Camera PID: 0x%x\n", s->id.PID);
    s->set_brightness(s, 1);     // Tăng độ sáng nhẹ
    s->set_contrast(s, 1);       // Tăng độ tương phản nhẹ
    s->set_saturation(s, 0);     // Màu sắc bình thường
    s->set_whitebal(s, 1);       // Bật cân bằng trắng tự động
    s->set_awb_gain(s, 1);       // Bật AWB gain
    s->set_wb_mode(s, 0);        // Auto white balance mode
    s->set_aec2(s, 1);           // Bật AEC DSP
    s->set_ae_level(s, 0);       // AE level mặc định
    s->set_gainceiling(s, (gainceiling_t)6); // Gain ceiling
  }

  Serial.println("Camera khởi động thành công!");
  return true;
}

// ===================== CORS HEADERS =====================
void sendCorsHeaders() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

// ===================== HTTP HANDLERS =====================

// Trang chủ - hiển thị thông tin hệ thống dạng HTML
void handleRoot() {
  sendCorsHeaders();
  
  // Dùng chuỗi Raw Literal (R"()") để viết HTML trực tiếp mà không cần cộng chuỗi String +=, giúp nhẹ RAM và code sạch hơn
  String html = R"rawliteral(
  <!DOCTYPE html><html><head>
  <title>Sentinel Eye - Control Panel</title>
  <meta charset='UTF-8'>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; text-align: center; background: #1a1a2e; color: #eee; padding: 20px; }
    h1 { color: #e94560; margin-bottom: 5px; }
    .info { background: #16213e; padding: 15px; border-radius: 10px; margin: 10px auto; max-width: 500px; text-align: left; }
    .btn { color: #0f3460; background: #e94560; padding: 10px 15px; border-radius: 5px; text-decoration: none; display: inline-block; margin: 5px; font-weight: bold; }
    .btn:hover { background: #c73650; color: #fff; }
    .status { color: #4ecca3; font-weight: bold; float: right; }
    .stream-box { margin-top: 20px; }
    .stream-img { max-width: 100%; border: 3px solid #e94560; border-radius: 10px; }
  </style></head><body>
  
  <h1>SENTINEL EYE</h1>
  <h3>ESP32-CAM Control Panel</h3>
  
  <div class='info'>
    <p>IP Address: <span class='status'>_IP_</span></p>
    <p>WiFi SSID: <span class='status'>_SSID_</span></p>
    <p>Signal Strength: <span class='status'>_RSSI_ dBm</span></p>
    <p>PSRAM Available: <span class='status'>_PSRAM_</span></p>
    <p>Alarm Buzzer: <span class='status'>_BUZZER_</span></p>
  </div>
  
  <div>
    <a href='/stream' class='btn' target='_blank'>Video Stream</a>
    <a href='/capture' class='btn' target='_blank'>Capture Image</a>
    <a href='/buzzer/on' class='btn'>Buzzer ON</a>
    <a href='/buzzer/off' class='btn'>Buzzer OFF</a>
    <a href='/status' class='btn' target='_blank'>JSON API</a>
  </div>
  
  <div class='stream-box'>
    <img src='/stream' class='stream-img'>
  </div>
  </body></html>
  )rawliteral";

  html.replace("_IP_", WiFi.localIP().toString());
  html.replace("_SSID_", String(ssid));
  html.replace("_RSSI_", String(WiFi.RSSI()));
  html.replace("_PSRAM_", psramFound() ? "YES" : "NO");
  html.replace("_BUZZER_", buzzerActive ? "ON" : "OFF");

  server.send(200, "text/html", html);
}

// MJPEG Stream - Python server sẽ đọc từ endpoint này
void handleStream() {
  WiFiClient client = server.client();
  
  // Lược bỏ NoDelay: Khi Stream khối dữ liệu lớn (như hình đoạn video), sử dụng cơ chế gộp gói mặc định 
  // của TCP giúp giảm số lượng Packet rác, băng thông Wi-Fi sẽ lưu thông mượt mà hơn.
  
  client.print("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\nAccess-Control-Allow-Origin: *\r\nCache-Control: no-cache\r\n\r\n");

  while (client.connected()) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      delay(5); // Nếu camera chưa cấp được khung hình, nghỉ 5ms để giải phóng CPU
      continue;
    }

    uint8_t * _jpg_buf = NULL;
    size_t _jpg_buf_len = 0;
    
    if (fb->format != PIXFORMAT_JPEG) {
      // Dùng búa tạ đập vỡ chất lượng hình ảnh về mốc 10. Hình bao dập hột (Blocky) nhưng tốc độ gói tin bay qua Wi-Fi là vô cực.
      bool jpeg_converted = frame2jpg(fb, 10, &_jpg_buf, &_jpg_buf_len);
      if (!jpeg_converted) {
        esp_camera_fb_return(fb);
        yield();
        continue;
      }
    } else {
      _jpg_buf = fb->buf;
      _jpg_buf_len = fb->len;
    }

    // In bằng bộ đệm printf giúp C++ giải quyết trong 1 nhịp Clock CPU thay vì cộng chuỗi String (++)
    client.printf("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
    client.write(_jpg_buf, _jpg_buf_len);
    client.print("\r\n");

    if (fb->format != PIXFORMAT_JPEG) {
      free(_jpg_buf);
    }
    esp_camera_fb_return(fb);
    
    // Nhận lệnh bật Còi giữa lúc đang truyền Video (Tối quan trọng để còi kêu song song với Stream)
    processBuzzerControl();
    
    // TỐI QUAN TRỌNG: Nghỉ 1 mili-giây nhường lõi phụ (Core 0) xử lý giao thức Wi-Fi 
    // -> Triệt tiêu hoàn toàn sự giật cục rớt mạng (Buffer Bloating/Watchdog resets).
    delay(1); 
  }
}

// Chụp 1 ảnh JPEG
void handleCapture() {
  sendCorsHeaders();
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  
  if (fb->format != PIXFORMAT_JPEG) {
    uint8_t * _jpg_buf = NULL;
    size_t _jpg_buf_len = 0;
    bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
    if(jpeg_converted) {
      server.sendHeader("Content-Disposition", "inline; filename=capture.jpg");
      server.send_P(200, "image/jpeg", (const char *)_jpg_buf, _jpg_buf_len);
      free(_jpg_buf);
    } else {
      server.send(500, "text/plain", "JPEG Software conversion failed");
    }
  } else {
    server.sendHeader("Content-Disposition", "inline; filename=capture.jpg");
    server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  }
  
  esp_camera_fb_return(fb);
}

// Bật Buzzer
void handleBuzzerOn() {
  sendCorsHeaders();
  digitalWrite(BUZZER_PIN, LOW); // Active LOW: truyền tín hiệu điện áp Âm (-) để chập mạch kích còi
  buzzerActive = true;
  Serial.println("BUZZER: ON");
  server.send(200, "application/json", "{\"buzzer\":\"on\",\"status\":\"ok\"}");
}

// Tắt Buzzer
void handleBuzzerOff() {
  sendCorsHeaders();
  digitalWrite(BUZZER_PIN, HIGH); // Nhả mức HIGH để tách mạch, còi nín
  buzzerActive = false;
  Serial.println("BUZZER: OFF");
  server.send(200, "application/json", "{\"buzzer\":\"off\",\"status\":\"ok\"}");
}

// Trạng thái hệ thống (JSON) - Dành cho Backend Python/NodeJS kiểm tra
void handleStatus() {
  sendCorsHeaders();
  
  // Dùng ngoặc kép nháy đơn kết hợp R"()" để in JSON sạch, không cần dùng dấu gạch chéo ngược (\") lằng nhằng
  String json = R"rawliteral({
    "device": "ESP32-CAM",
    "project": "Sentinel Eye",
    "ip": "_IP_",
    "rssi": _RSSI_,
    "psram": _PSRAM_,
    "buzzer": "_BUZZER_",
    "uptime": _UPTIME_
  })rawliteral";
  
  json.replace("_IP_", WiFi.localIP().toString());
  json.replace("_RSSI_", String(WiFi.RSSI()));
  json.replace("_PSRAM_", psramFound() ? "true" : "false");
  json.replace("_BUZZER_", buzzerActive ? "on" : "off");
  json.replace("_UPTIME_", String(millis() / 1000));
  
  server.send(200, "application/json", json);
}

// Xử lý OPTIONS (CORS preflight)
void handleOptions() {
  sendCorsHeaders();
  server.send(204);
}

// Xử lý tín hiệu còi chèn vào giữa lúc đang Stream video liên tục (Dùng riêng port 81)
void processBuzzerControl() {
  WiFiClient ctrlClient = controlServer.available();
  if (ctrlClient) {
    String request = ctrlClient.readStringUntil('\r');
    ctrlClient.flush();
    ctrlClient.println("HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\nOK");
    ctrlClient.stop(); // Trả lời nhanh gọn để tránh tắc luồng
    
    if (request.indexOf("/buzzer/on") != -1) {
      digitalWrite(BUZZER_PIN, LOW); // Active LOW: bật còi
      buzzerActive = true;
      Serial.println("BUZZER: ON (Khẩn cấp qua Port 81)");
    } else if (request.indexOf("/buzzer/off") != -1) {
      digitalWrite(BUZZER_PIN, HIGH); // Tắt còi
      buzzerActive = false;
      Serial.println("BUZZER: OFF (Khẩn cấp qua Port 81)");
    }
  }
}

// ===================== SETUP =====================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Tắt cảm biến sụt áp (Brownout) đầu tiên tránh lỗi reset do laptop Dell dòng yếu
  delay(1000); 

  Serial.begin(115200);
  delay(500); 
  Serial.println("\n\n================================");
  Serial.println("   SENTINEL EYE - Starting...");
  Serial.println("================================\n");

  // Khởi tạo Buzzer pin (Còi của bạn là loại kích mức thấp - Active LOW)
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, HIGH); // Để điện áp ở mức CAO còi mới chịu tắt (Im lặng)
  Serial.println("[OK] Buzzer pin (GPIO 14) initialized");

  // Khởi tạo Camera
  if (!initCamera()) {
    Serial.println("[FAIL] Camera init failed! Restarting...");
    delay(3000);
    ESP.restart();
  }

  // Kết nối WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("[...] Đang kết nối WiFi: ");
  Serial.println(ssid);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n[FAIL] WiFi connection failed! Restarting...");
    delay(3000);
    ESP.restart();
  }

  // Loại bỏ chế độ ép xung WiFi để chống nóng cho mạch khi chạy 24/7

  Serial.println();
  Serial.println("[OK] WiFi connected!");
  Serial.print("[OK] IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("[OK] Signal Strength: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");

  // Đăng ký các HTTP endpoints
  server.on("/", HTTP_GET, handleRoot);
  server.on("/stream", HTTP_GET, handleStream);
  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/buzzer/on", HTTP_GET, handleBuzzerOn);
  server.on("/buzzer/off", HTTP_GET, handleBuzzerOff);
  server.on("/status", HTTP_GET, handleStatus);

  // CORS preflight
  server.on("/buzzer/on", HTTP_OPTIONS, handleOptions);
  server.on("/buzzer/off", HTTP_OPTIONS, handleOptions);
  server.on("/status", HTTP_OPTIONS, handleOptions);

  server.begin();
  controlServer.begin(); // Khởi tạo port 81 phụ trách báo cháy

  // Beep ngắn để xác nhận khởi động thành công (Logic Active LOW)
  digitalWrite(BUZZER_PIN, LOW);   // Kêu
  delay(100);
  digitalWrite(BUZZER_PIN, HIGH);  // Im
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);   // Kêu
  delay(100);
  digitalWrite(BUZZER_PIN, HIGH);  // Im lặng hẳn chờ cảnh báo từ Laptop

  Serial.println("\n================================");
  Serial.println("   SENTINEL EYE - Ready!");
  Serial.println("================================");
  Serial.println("Endpoints:");
  Serial.println("  /         - Control Panel");
  Serial.println("  /stream   - MJPEG Video Stream");
  Serial.println("  /capture  - Chụp 1 ảnh");
  Serial.println("  /buzzer/on  - Bật còi");
  Serial.println("  /buzzer/off - Tắt còi");
  Serial.println("  /status   - Trạng thái JSON");
  Serial.println("================================\n");
}

// ===================== LOOP =====================
void loop() {
  server.handleClient();
  processBuzzerControl(); // Quét lệnh còi bình thường khi rảnh

  // Kiểm tra WiFi và tự kết nối lại nếu mất
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WARN] WiFi disconnected! Reconnecting...");
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n[OK] WiFi reconnected!");
      Serial.print("[OK] IP: ");
      Serial.println(WiFi.localIP());
    }
  }
}