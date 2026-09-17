# 🛡️ SENTINEL EYE — Báo Cáo Dự Án

## Hệ Thống Giám Sát An Ninh Thông Minh với AI Virtual Fence

> **Môn học:** Tương tác Người và Máy (HCI)  
> **Công nghệ:** ESP32-CAM · YOLOv8 · Flask · OpenCV · PlatformIO

---

## 📋 Mục Lục

1. [Tổng Quan Dự Án](#1-tổng-quan-dự-án)
2. [Kiến Trúc Hệ Thống](#2-kiến-trúc-hệ-thống)
3. [Phần Cứng — ESP32-CAM Firmware](#3-phần-cứng--esp32-cam-firmware)
4. [Phần Mềm — Flask Backend Server](#4-phần-mềm--flask-backend-server)
5. [Nhận Diện Người — YOLOv8](#5-nhận-diện-người--yolov8)
6. [Virtual Fence — Hàng Rào Ảo](#6-virtual-fence--hàng-rào-ảo)
7. [Hệ Thống Cảnh Báo Tự Động](#7-hệ-thống-cảnh-báo-tự-động)
8. [Ghi Log Xâm Nhập](#8-ghi-log-xâm-nhập)
9. [Web Dashboard](#9-web-dashboard)
10. [API Endpoints](#10-api-endpoints)
11. [Cấu Trúc Thư Mục](#11-cấu-trúc-thư-mục)
12. [Công Nghệ Sử Dụng](#12-công-nghệ-sử-dụng)

---

## 1. Tổng Quan Dự Án

**SENTINEL EYE** là hệ thống giám sát an ninh thông minh kết hợp phần cứng IoT (ESP32-CAM) và trí tuệ nhân tạo (YOLOv8) để:

- **Stream video trực tiếp** từ camera ESP32-CAM qua WiFi
- **Nhận diện người** trong video bằng mô hình YOLOv8 (deep learning)
- **Thiết lập vùng cấm (Virtual Fence)** bằng cách vẽ polygon trên giao diện web
- **Phát hiện xâm nhập** khi có người bước vào vùng cấm
- **Tự động cảnh báo** bằng còi buzzer trên ESP32 + cảnh báo âm thanh/hình ảnh trên web
- **Ghi log lịch sử** xâm nhập kèm ảnh chụp tự động

---

## 2. Kiến Trúc Hệ Thống

```
┌─────────────────────┐    WiFi/HTTP     ┌──────────────────────┐    HTTP     ┌──────────────┐
│   ESP32-CAM         │ ──────────────▶  │   Flask Server       │ ─────────▶ │  Web Browser │
│   (Phần cứng)       │                  │   (Python Backend)   │            │  (Dashboard) │
│                     │ ◀──────────────  │                      │            │              │
│  • Camera OV3660    │  Buzzer control   │  • MJPEG Stream      │            │  • Live View │
│  • Buzzer GPIO 12   │                  │  • YOLOv8 Detection  │            │  • Controls  │
│  • WiFi             │                  │  • Virtual Fence     │            │  • Alerts    │
│  • Web Server       │                  │  • Alert System      │            │  • Logs      │
└─────────────────────┘                  │  • Intrusion Logging │            └──────────────┘
                                         └──────────────────────┘
```

**Luồng hoạt động:**
1. ESP32-CAM stream video MJPEG qua endpoint `/stream`
2. Flask Server đọc stream, lưu frame vào bộ nhớ
3. Thread YOLO detection phân tích frame → phát hiện người
4. Kiểm tra foot-point của mỗi người có nằm trong polygon vùng cấm không (Point-in-Polygon)
5. Nếu có xâm nhập → tự động bật buzzer + lưu ảnh + ghi log
6. Web Dashboard hiển thị video đã vẽ bounding box + cảnh báo trực quan

---

## 3. Phần Cứng — ESP32-CAM Firmware

**File:** `HCI_Camera_Test/src/main.cpp`  
**Platform:** PlatformIO · ESP32 · Arduino Framework

### 3.1 Cấu hình phần cứng

| Thành phần | Chi tiết |
|---|---|
| Board | AI-Thinker ESP32-CAM |
| Camera | OV3660 (VGA 640×480 nếu có PSRAM, QVGA 320×240 nếu không) |
| Buzzer | Active Buzzer → GPIO 12 + GND |
| WiFi | 2.4GHz, kết nối qua SSID/Password cấu hình trong code |

### 3.2 Các endpoint HTTP trên ESP32

| Endpoint | Method | Mô tả |
|---|---|---|
| `/` | GET | Trang Control Panel đơn giản trên ESP32 |
| `/stream` | GET | MJPEG video stream liên tục |
| `/capture` | GET | Chụp 1 ảnh JPEG |
| `/buzzer/on` | GET | Bật còi buzzer |
| `/buzzer/off` | GET | Tắt còi buzzer |
| `/status` | GET | Trạng thái hệ thống (JSON): IP, RSSI, PSRAM, buzzer, uptime |

### 3.3 Tính năng firmware

- **Khởi tạo camera** với cấu hình tối ưu (độ sáng, tương phản, cân bằng trắng)
- **CORS headers** cho phép Flask server gọi API cross-origin
- **Tự động kết nối lại WiFi** khi mất kết nối trong `loop()`
- **Beep xác nhận khởi động** — 2 tiếng beep ngắn khi boot thành công
- **Double buffer** (nếu có PSRAM) để stream mượt hơn

---

## 4. Phần Mềm — Flask Backend Server

**File:** `server/app.py`  
**Config:** `server/config.py`

### 4.1 Kiến trúc đa luồng (Multi-threading)

Server sử dụng 3 thread chạy song song:

| Thread | Chức năng |
|---|---|
| **Stream Reader** | Đọc MJPEG stream từ ESP32-CAM liên tục, lưu frame vào `current_frame` |
| **YOLO Detection** | Lấy frame → chạy YOLOv8 → vẽ bounding box → kiểm tra xâm nhập → lưu vào `detected_frame` |
| **Flask Main** | Phục vụ Web Dashboard, API endpoints, MJPEG stream cho browser |

### 4.2 Xử lý Stream

- Đọc MJPEG stream bằng `requests.get(stream=True)`
- Parse JPEG frame từ byte stream (tìm marker `FFD8` → `FFD9`)
- Decode bằng OpenCV `cv2.imdecode()`
- Tự động kết nối lại khi mất kết nối (retry mỗi 3 giây)
- Tính FPS stream real-time

### 4.3 Cấu hình (`config.py`)

| Tham số | Giá trị mặc định | Mô tả |
|---|---|---|
| `ESP32_IP` | `192.168.1.113` | Địa chỉ IP của ESP32-CAM |
| `SERVER_PORT` | `5000` | Port Flask server |
| `YOLO_MODEL` | `yolov8n.pt` | Model YOLO (nano - nhẹ nhất) |
| `YOLO_CONFIDENCE` | `0.45` | Ngưỡng tin cậy detection (0.0 - 1.0) |
| `YOLO_DETECT_INTERVAL` | `2` | Chạy YOLO mỗi N frame |
| `ALERT_COOLDOWN_SECONDS` | `3` | Cooldown giữa 2 lần cảnh báo |
| `BUZZER_DURATION_SECONDS` | `3` | Thời gian kêu còi mỗi lần |
| `MAX_LOG_IMAGES` | `500` | Số ảnh log tối đa (tự xóa cũ) |

---

## 5. Nhận Diện Người — YOLOv8

### 5.1 Model

- **YOLOv8n (Nano)** — phiên bản nhẹ nhất của Ultralytics YOLOv8
- Được train sẵn trên **COCO dataset** (80 class, class 0 = "person")
- Chạy trên **CPU** (không cần GPU)
- File model: `yolov8n.pt` (~6MB)

### 5.2 Quy trình detection

```
Frame từ ESP32 → YOLOv8 Inference → Lọc class "person" → 
→ Tính foot-point (trung điểm đáy bounding box) →
→ Kiểm tra Point-in-Polygon → Vẽ bounding box + label
```

### 5.3 Kết quả detection

Mỗi người phát hiện được lưu dạng:
```json
{
    "bbox": [x1, y1, x2, y2],
    "confidence": 0.87,
    "foot_point": [320, 450],
    "intruding": true
}
```

### 5.4 Hiển thị

| Trạng thái | Bounding Box | Label | Foot Point |
|---|---|---|---|
| An toàn | Xanh lá, nét 2px | `Person 87%` (nền xanh) | Cam |
| Xâm nhập | Đỏ, nét 3px | `INTRUSION 87%` (nền đỏ) | Đỏ |

---

## 6. Virtual Fence — Hàng Rào Ảo

### 6.1 Nguyên lý

- Người dùng **vẽ polygon** (đa giác) trên giao diện web => định nghĩa vùng cấm
- Tọa độ được **chuẩn hóa (0.0 - 1.0)** để không phụ thuộc vào resolution
- Sử dụng thuật toán **Ray Casting** để kiểm tra điểm (foot-point người) có nằm trong polygon không

### 6.2 Ray Casting Algorithm

```
Bắn 1 tia từ điểm cần kiểm tra sang phải vô cực.
Đếm số lần tia cắt cạnh polygon:
  - Số lẻ → điểm nằm TRONG polygon
  - Số chẵn → điểm nằm NGOÀI polygon
```

### 6.3 Foot-Point

- Vị trí "chân người" = **trung điểm cạnh dưới** bounding box
- `foot_x = (x1 + x2) / 2`, `foot_y = y2`
- Dùng foot-point thay vì center-point vì chân người tiếp xúc mặt đất = vị trí thực tế

### 6.4 Hiển thị trên video

- Vùng cấm: tô đỏ nhạt bán trong suốt (alpha 25%)
- Viền: nét đỏ đậm 2px
- Các đỉnh (vertex): chấm vàng
- Nhãn: **"RESTRICTED ZONE"** ở tâm polygon

---

## 7. Hệ Thống Cảnh Báo Tự Động

### 7.1 Cảnh báo phần cứng (Buzzer ESP32)

- Khi phát hiện xâm nhập → gửi HTTP request `GET /buzzer/on` tới ESP32
- Sau `BUZZER_DURATION_SECONDS` (3s) → gửi `GET /buzzer/off`
- **Cooldown**: tối thiểu `ALERT_COOLDOWN_SECONDS` (3s) giữa 2 lần cảnh báo
- Chạy trên **thread riêng** để không block detection

### 7.2 Cảnh báo trên Dashboard

| Loại cảnh báo | Mô tả |
|---|---|
| **Alert Banner** | Thanh đỏ nhấp nháy phía trên trang: "🚨 INTRUSION DETECTED" |
| **Âm thanh web** | 3 tiếng beep (880Hz, Web Audio API) — không cần file âm thanh |
| **Intrusion Badge** | Badge đỏ trên header hiển thị số người xâm nhập |
| **Detection List** | Mỗi người hiển thị trạng thái `INTRUDING` (đỏ) hoặc `safe` |
| **Activity Log** | Ghi nhận sự kiện xâm nhập vào log panel |

### 7.3 Bật/tắt

- Nút **"Auto Alert: ON/OFF"** trên Dashboard
- API: `GET /api/alert/toggle`
- Nút **"Test Alert"** để thử nghiệm buzzer

---

## 8. Ghi Log Xâm Nhập

### 8.1 Dữ liệu lưu trữ

Mỗi sự kiện xâm nhập lưu:

```json
{
    "time": "2026-03-10 14:30:25",
    "count": 2,
    "image": "intrusion_20260310_143025.jpg"
}
```

### 8.2 Lưu trữ

| Loại | Vị trí | Mô tả |
|---|---|---|
| **Ảnh JPEG** | `intrusion_logs/intrusion_YYYYMMDD_HHMMSS.jpg` | Ảnh frame có bounding box tại thời điểm xâm nhập |
| **Log JSON** | `intrusion_logs/intrusion_log.json` | Danh sách toàn bộ sự kiện, persist qua restart |
| **RAM** | Biến `intrusion_log` | 200 entries gần nhất để phục vụ API nhanh |

### 8.3 Quản lý dung lượng

- Tự động xóa ảnh cũ nhất khi vượt quá `MAX_LOG_IMAGES` (500 ảnh)
- Log JSON được load lại khi server khởi động

### 8.4 Xem lịch sử

- Panel **"Intrusion History"** trên Dashboard
- Mỗi entry hiển thị: thời gian + số người xâm nhập + link xem ảnh
- Nút **Refresh** và **Clear All**

---

## 9. Web Dashboard

### 9.1 Giao diện

Giao diện web tối (dark theme) chuyên nghiệp gồm:

| Khu vực | Mô tả |
|---|---|
| **Header** | Logo SENTINEL EYE + trạng thái kết nối ESP32 + Person count + Intrusion count + FPS |
| **Alert Banner** | Thanh cảnh báo đỏ nhấp nháy (ẩn khi không có xâm nhập) |
| **Video Panel** | Stream video trực tiếp với bounding box + fence overlay + canvas vẽ fence |
| **System Info** | IP, trạng thái ESP32, WiFi RSSI, Stream/Detect FPS, Person count, Intrusion count, Auto Alert |
| **AI Detection** | Toggle YOLO ON/OFF + Confidence Threshold slider |
| **Detected Persons** | Danh sách người phát hiện với % confidence + trạng thái xâm nhập |
| **Virtual Fence** | Draw/Undo/Clear/Save fence + thông tin số điểm + trạng thái |
| **Controls** | Buzzer ON/OFF + Chụp ảnh + Auto Alert toggle + Test Alert |
| **Intrusion History** | Lịch sử xâm nhập với ảnh + Refresh/Clear |
| **Activity Log** | Console log sự kiện hệ thống (max 50 entries) |

### 9.2 Tính năng tương tác (HCI)

- **Vẽ fence bằng click** — chế độ Drawing Mode với crosshair cursor
- **Real-time status** — auto-refresh mỗi 2 giây
- **Responsive** — hỗ trợ mobile (flex column khi < 900px)
- **Visual feedback** — animation, color coding, badge updates
- **Audio feedback** — beep cảnh báo qua Web Audio API
- **Canvas overlay** — fence hiển thị trên video, resize tự động

---

## 10. API Endpoints

### Flask Server (`http://localhost:5000`)

| Endpoint | Method | Mô tả |
|---|---|---|
| `/` | GET | Web Dashboard |
| `/video_feed` | GET | MJPEG stream (với detection overlay) |
| `/api/status` | GET | Trạng thái toàn hệ thống (JSON) |
| `/api/detections` | GET | Danh sách detection hiện tại |
| `/api/yolo/toggle` | GET | Bật/tắt YOLO detection |
| `/api/yolo/confidence/<value>` | GET | Đặt ngưỡng confidence (0.0 - 1.0) |
| `/api/snapshot` | GET | Chụp ảnh frame hiện tại |
| `/api/fence/set` | POST | Lưu polygon vùng cấm (JSON body) |
| `/api/fence/get` | GET | Lấy polygon hiện tại |
| `/api/fence/clear` | GET | Xóa polygon |
| `/api/alert/toggle` | GET | Bật/tắt tự động cảnh báo |
| `/api/alert/test` | GET | Test buzzer cảnh báo |
| `/api/logs` | GET | Lấy lịch sử xâm nhập (50 gần nhất) |
| `/api/logs/clear` | GET | Xóa toàn bộ log |
| `/api/logs/image/<file>` | GET | Xem ảnh xâm nhập |
| `/api/esp32/buzzer/on` | GET | Bật buzzer qua ESP32 |
| `/api/esp32/buzzer/off` | GET | Tắt buzzer qua ESP32 |

---

## 11. Cấu Trúc Thư Mục

```
HCL/
├── BÁO_CÁO_DỰ_ÁN.md              ← File này
├── HƯỚNG_DẪN_SỬ_DỤNG.md           ← Hướng dẫn sử dụng
├── yolov8n.pt                       ← Model YOLO (backup)
├── intrusion_logs/                  ← Thư mục log (root)
│
└── server/                          ← Flask Backend
    ├── app.py                       ← Server chính (510+ dòng)
    ├── config.py                    ← Cấu hình tập trung
    ├── requirements.txt             ← Python dependencies
    ├── yolov8n.pt                   ← Model YOLO
    ├── intrusion_logs/              ← Ảnh + log xâm nhập
    │   ├── intrusion_log.json       ← Log JSON
    │   └── intrusion_*.jpg          ← Ảnh xâm nhập
    └── templates/
        └── index.html               ← Web Dashboard (700+ dòng)

HCI_Camera_Test/                     ← PlatformIO Project
├── platformio.ini                   ← Config PlatformIO (esp32cam)
├── src/
│   └── main.cpp                     ← ESP32-CAM Firmware (330+ dòng)
├── include/
├── lib/
└── test/
```

---

## 12. Công Nghệ Sử Dụng

### Phần cứng
| Công nghệ | Mục đích |
|---|---|
| ESP32-CAM (AI-Thinker) | Camera module + WiFi + GPIO |
| Active Buzzer | Cảnh báo âm thanh vật lý |
| PlatformIO + Arduino | Framework lập trình firmware |

### Phần mềm Backend
| Công nghệ | Version | Mục đích |
|---|---|---|
| Python | 3.x | Ngôn ngữ backend |
| Flask | 3.1.0 | Web framework |
| Flask-CORS | 5.0.1 | Cross-Origin Resource Sharing |
| OpenCV | 4.10.0 | Xử lý ảnh, encode/decode JPEG |
| NumPy | 2.2.3 | Xử lý mảng, tính toán |
| Requests | 2.32.3 | HTTP client (gọi ESP32 API) |
| Ultralytics | latest | YOLO detection engine |
| YOLOv8n | v8 nano | Model nhận diện đối tượng |

### Frontend
| Công nghệ | Mục đích |
|---|---|
| HTML5 / CSS3 | Giao diện Dashboard |
| JavaScript (vanilla) | Logic tương tác, fetch API |
| Canvas API | Vẽ fence overlay trên video |
| Web Audio API | Âm thanh cảnh báo trên trình duyệt |

### Thuật toán
| Thuật toán | Mục đích |
|---|---|
| YOLOv8 (Deep Learning) | Nhận diện người trong video |
| Ray Casting | Kiểm tra điểm trong polygon (Point-in-Polygon) |
| MJPEG Parsing | Tách frame JPEG từ stream byte |
| Coordinate Normalization | Chuẩn hóa tọa độ fence (0.0-1.0) |

---

> **SENTINEL EYE** — Hệ thống giám sát an ninh hoàn chỉnh, kết hợp IoT + AI + Web trong một dự án tương tác Người và Máy.
