# 🛡️ SENTINEL EYE — Hướng Dẫn Sử Dụng

## Hệ Thống Giám Sát An Ninh Thông Minh

---

## 📋 Mục Lục

1. [Yêu Cầu Hệ Thống](#1-yêu-cầu-hệ-thống)
2. [Lắp Ráp Phần Cứng](#2-lắp-ráp-phần-cứng)
3. [Nạp Firmware cho ESP32-CAM](#3-nạp-firmware-cho-esp32-cam)
4. [Cài Đặt Python Server](#4-cài-đặt-python-server)
5. [Cấu Hình Hệ Thống](#5-cấu-hình-hệ-thống)
6. [Chạy Hệ Thống](#6-chạy-hệ-thống)
7. [Sử Dụng Dashboard](#7-sử-dụng-dashboard)
8. [Thiết Lập Virtual Fence](#8-thiết-lập-virtual-fence)
9. [Hệ Thống Cảnh Báo](#9-hệ-thống-cảnh-báo)
10. [Xem Lịch Sử Xâm Nhập](#10-xem-lịch-sử-xâm-nhập)
11. [Sử Dụng API](#11-sử-dụng-api)
12. [Khắc Phục Sự Cố](#12-khắc-phục-sự-cố)

---

## 1. Yêu Cầu Hệ Thống

### Phần cứng cần có

| Thành phần | Mô tả | Ghi chú |
|---|---|---|
| **ESP32-CAM** | Board AI-Thinker ESP32-CAM | Có PSRAM để chạy VGA 640×480 |
| **Active Buzzer** | Buzzer 3.3V hoặc 5V | Nối vào GPIO 12 và GND |
| **USB-TTL Adapter** | Để nạp firmware (FTDI/CP2102/CH340) | Nạp xong có thể tháo |
| **Nguồn 5V** | Cấp nguồn cho ESP32-CAM | USB hoặc adapter 5V/1A |
| **Dây jumper** | Kết nối buzzer | 2 dây (signal + GND) |

### Phần mềm cần cài

| Phần mềm | Version | Link tải |
|---|---|---|
| **Python** | 3.8 trở lên | https://www.python.org/downloads/ |
| **VS Code** | Mới nhất | https://code.visualstudio.com/ |
| **PlatformIO Extension** | Mới nhất | Cài trong VS Code Extensions |
| **Trình duyệt web** | Chrome/Edge/Firefox | Bất kỳ trình duyệt hiện đại |

### Mạng

- Máy tính và ESP32-CAM phải **cùng mạng WiFi**
- WiFi 2.4GHz (ESP32 không hỗ trợ 5GHz)

---

## 2. Lắp Ráp Phần Cứng

### Sơ đồ kết nối Buzzer

```
ESP32-CAM          Active Buzzer
─────────          ─────────────
 GPIO 12  ───────  (+) Signal
 GND      ───────  (−) GND
```

### Sơ đồ nạp firmware (qua USB-TTL)

```
USB-TTL Adapter      ESP32-CAM
───────────────      ─────────
 TX        ───────   U0R (GPIO 3)
 RX        ───────   U0T (GPIO 1)
 GND       ───────   GND
 5V        ───────   5V

⚠️ QUAN TRỌNG: Nối GPIO 0 → GND trước khi nạp firmware!
   Tháo jumper GPIO0-GND sau khi nạp xong, rồi nhấn RESET.
```

---

## 3. Nạp Firmware cho ESP32-CAM

### Bước 1: Mở project PlatformIO

1. Mở VS Code
2. Mở thư mục: `HCI_Camera_Test/`
3. PlatformIO sẽ tự nhận diện project

### Bước 2: Cấu hình WiFi

Mở file `src/main.cpp`, tìm dòng sau và sửa thành WiFi nhà bạn:

```cpp
const char* ssid = "Tên_WiFi_của_bạn";
const char* password = "Mật_khẩu_WiFi";
```

### Bước 3: Nạp firmware

1. Nối dây USB-TTL theo sơ đồ trên
2. **Nối GPIO 0 → GND** (chế độ flash)
3. Nhấn nút **RESET** trên ESP32-CAM
4. Trong VS Code, nhấn nút **Upload** (→) trên thanh PlatformIO
5. Chờ nạp xong (hiện "SUCCESS")
6. **Tháo dây GPIO 0 ↔ GND**
7. Nhấn **RESET** để chạy firmware

### Bước 4: Kiểm tra

1. Mở **Serial Monitor** (biểu tượng ổ cắm trên PlatformIO)
2. Baud rate: **115200**
3. Bạn sẽ thấy:
```
================================
   SENTINEL EYE - Starting...
================================

[OK] Buzzer pin (GPIO 12) initialized
PSRAM found! Sử dụng VGA 640x480
Camera khởi động thành công!
[OK] WiFi connected!
[OK] IP Address: 192.168.1.XXX    ← GHI LẠI IP NÀY!
[OK] Signal Strength: -45 dBm

================================
   SENTINEL EYE - Ready!
================================
```

4. **Ghi lại địa chỉ IP** hiện trên Serial Monitor (ví dụ: `192.168.1.113`)
5. Mở trình duyệt web, truy cập `http://192.168.1.XXX` để test camera

---

## 4. Cài Đặt Python Server

### Bước 1: Mở terminal tại thư mục server

```bash
cd HCL/server
```

### Bước 2: Tạo virtual environment (khuyến nghị)

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### Bước 3: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Danh sách thư viện sẽ được cài:
- `flask` — Web framework
- `flask-cors` — Cross-origin support
- `opencv-python` — Xử lý ảnh
- `numpy` — Tính toán mảng
- `requests` — HTTP client
- `ultralytics` — YOLOv8 engine (sẽ tự tải model lần đầu)

### Bước 4: Kiểm tra model YOLO

File `yolov8n.pt` phải nằm trong thư mục `server/`. Nếu chưa có, `ultralytics` sẽ tự tải khi chạy lần đầu.

---

## 5. Cấu Hình Hệ Thống

Mở file `server/config.py` và chỉnh sửa:

### 5.1 Cấu hình ESP32 (BẮT BUỘC)

```python
# ⚠️ THAY ĐỔI IP NÀY cho đúng với IP ESP32-CAM của bạn
ESP32_IP = "192.168.1.113"
```

> IP này lấy từ Serial Monitor ở Bước 3.4

### 5.2 Cấu hình YOLO (tùy chỉnh)

```python
YOLO_CONFIDENCE = 0.45      # Tăng lên (0.6-0.8) nếu bị nhận nhầm
                             # Giảm xuống (0.3) nếu không nhận ra người
YOLO_DETECT_INTERVAL = 2    # Tăng lên (3-5) nếu CPU yếu/lag
                             # Giảm xuống (1) nếu cần nhanh hơn
```

### 5.3 Cấu hình cảnh báo (tùy chỉnh)

```python
ALERT_COOLDOWN_SECONDS = 3   # Khoảng cách giữa 2 lần cảnh báo
BUZZER_DURATION_SECONDS = 3  # Thời gian còi kêu
MAX_LOG_IMAGES = 500         # Số ảnh log tối đa
```

---

## 6. Chạy Hệ Thống

### Bước 1: Đảm bảo ESP32-CAM đang chạy

- ESP32 phải được cấp nguồn và kết nối WiFi
- Kiểm tra bằng cách mở `http://<ESP32_IP>/status` trên trình duyệt

### Bước 2: Chạy Flask Server

```bash
cd HCL/server
python app.py
```

Bạn sẽ thấy output:

```
[YOLO] Đang tải model yolov8n.pt...
[YOLO] Model loaded thành công!

=======================================================
   SENTINEL EYE - Python Server (YOLO Enabled)
=======================================================
  Server:     http://localhost:5000
  ESP32:      192.168.1.113
  YOLO Model: yolov8n.pt
  Confidence: 0.45
  Detect Every: 2 frame(s)
=======================================================
```

### Bước 3: Mở Dashboard

Mở trình duyệt web và truy cập:

```
http://localhost:5000
```

> 💡 Nếu muốn truy cập từ thiết bị khác cùng mạng, dùng IP máy tính thay `localhost`:
> Ví dụ: `http://192.168.1.100:5000`

---

## 7. Sử Dụng Dashboard

### 7.1 Tổng quan giao diện

Khi mở Dashboard, bạn sẽ thấy:

```
┌─────────────────────────────────────────────────────────┐
│  🛡️ SENTINEL EYE    [●Connected] [Persons:2] [0 FPS]   │  ← Header
├─────────────────────────────────────────────────────────┤
│  🚨 INTRUSION DETECTED — RESTRICTED ZONE BREACHED 🚨   │  ← Alert (khi có xâm nhập)
├──────────────────────────┬──────────────────────────────┤
│                          │  📊 System Info              │
│   📹 Live Camera Feed   │  🤖 AI Detection             │
│                          │  👤 Detected Persons         │
│   [Video Stream + YOLO   │  ⚠️ Virtual Fence            │
│    bounding boxes]       │  🎮 Controls                 │
│                          │  📜 Intrusion History        │
│                          │  📋 Activity Log             │
└──────────────────────────┴──────────────────────────────┘
```

### 7.2 Header — Thanh trạng thái

| Phần tử | Ý nghĩa |
|---|---|
| **●Connected / ●Disconnected** | Trạng thái kết nối ESP32 (xanh = online, đỏ = offline) |
| **Persons: N** | Số người phát hiện được trong frame hiện tại |
| **Intruders: N** | Số người đang xâm nhập vùng cấm (badge đỏ) |
| **X FPS** | Tốc độ stream từ ESP32 |

### 7.3 Video Panel

- Hiển thị **video trực tiếp** từ camera
- Nếu YOLO bật: có **bounding box** xung quanh người
  - 🟩 Hộp xanh = an toàn
  - 🟥 Hộp đỏ = xâm nhập vùng cấm
- **Foot point** (chấm tròn) = vị trí chân người
- **Vùng cấm** hiển thị đỏ nhạt với viền đỏ + nhãn "RESTRICTED ZONE"
- **Info bar** phía trên: số người + FPS + cảnh báo

### 7.4 Panel AI Detection

- Nút **"🧠 Toggle YOLO ON/OFF"**: bật/tắt nhận diện AI
- **Confidence Threshold** (thanh trượt): điều chỉnh ngưỡng tin cậy
  - Kéo sang phải (0.7-0.9): chỉ nhận diện khi chắc chắn
  - Kéo sang trái (0.2-0.4): nhạy hơn nhưng có thể nhận nhầm

### 7.5 Panel Detected Persons

Danh sách mỗi người được nhận diện:
- **👤 Person 1** — 87% — `safe` (an toàn)
- **👤 Person 2 ⚠️** — 92% — `INTRUDING` (xâm nhập, chữ đỏ)

---

## 8. Thiết Lập Virtual Fence

Đây là tính năng quan trọng nhất — định nghĩa **vùng cấm** mà người không được phép vào.

### Bước 1: Bật Drawing Mode

1. Tìm panel **"⚠️ Virtual Fence"** bên phải
2. Nhấn nút **"✏️ Draw Fence"**
3. Nút chuyển thành **"⏹️ Stop Drawing"** nhấp nháy đỏ
4. Con trỏ chuột trên video chuyển thành hình **crosshair (+)**
5. Trên video hiện dòng: **"🔶 DRAWING MODE — Click to add points"**

### Bước 2: Vẽ vùng cấm

1. **Click vào video** để đặt các điểm polygon
2. Điểm đầu tiên: hiện **chấm xanh lá** (điểm bắt đầu)
3. Các điểm tiếp theo: hiện **chấm cam** + số thứ tự
4. Khi có **≥ 3 điểm**: vùng polygon hiển thị đỏ nhạt

**Mẹo vẽ:**
- Vẽ **4–6 điểm** là đủ cho hầu hết trường hợp
- Vẽ theo **chiều kim đồng hồ hoặc ngược** đều được
- Bao phủ khu vực bạn muốn **cấm** (cửa ra vào, hành lang, kho,...)

### Bước 3: Chỉnh sửa (nếu cần)

- **"↩️ Undo"**: xóa điểm cuối cùng
- **"🗑️ Clear"**: xóa toàn bộ để vẽ lại

### Bước 4: Lưu Fence

1. Nhấn **"💾 Save Fence"**
2. Log hiện: `"Fence saved: N points → RESTRICTED ZONE active"`
3. Trạng thái chuyển thành: **"Active (N pts)"** (chữ đỏ)
4. Drawing Mode tự động tắt
5. Từ bây giờ, nếu chân người bước vào vùng đỏ → **INTRUSION!**

### Ví dụ minh họa

```
Giả sử bạn muốn cấm khu vực cửa phòng:

  ┌──────────────── Camera View ─────────────────┐
  │                                               │
  │    ┌─ ─ ─ ─ ─ ─ ─┐                          │
  │    │ 1●          2●│                          │
  │    │   RESTRICTED  │                          │
  │    │     ZONE      │   👤 (an toàn - xanh)   │
  │    │              │                           │
  │    │ 4●          3●│                          │
  │    └─ ─ ─ ─ ─ ─ ─┘                          │
  │                         👤⚠️ (xâm nhập - đỏ)  │
  │         (nếu chân người ở trong vùng đỏ)      │
  └───────────────────────────────────────────────┘
```

---

## 9. Hệ Thống Cảnh Báo

### 9.1 Cảnh báo tự động

Khi có người **bước vào vùng cấm**:

1. 🔴 **Thanh đỏ nhấp nháy** xuất hiện trên đầu trang: "🚨 INTRUSION DETECTED"
2. 🔊 **3 tiếng beep** phát ra từ loa trình duyệt (Web Audio)
3. 🔔 **Buzzer trên ESP32** tự động kêu trong 3 giây
4. 📸 **Ảnh xâm nhập** tự động được chụp và lưu
5. 📝 **Log** được ghi lại (thời gian + số người)

### 9.2 Bật/tắt Auto Alert

- Nhấn nút **"🚨 Auto Alert: ON/OFF"** trong panel Controls
- Khi tắt: vẫn nhận diện xâm nhập nhưng **không** bật buzzer hay lưu ảnh
- Hữu ích khi đang test hoặc debug

### 9.3 Test Alert

- Nhấn nút **"🔊 Test Alert"** để thử buzzer
- Buzzer sẽ kêu 3 giây rồi tự tắt
- Dùng để kiểm tra kết nối buzzer hoạt động tốt không

### 9.4 Điều khiển Buzzer thủ công

- **"🔔 Buzzer ON"**: bật buzzer (kêu liên tục cho đến khi tắt)
- **"🔕 Buzzer OFF"**: tắt buzzer

---

## 10. Xem Lịch Sử Xâm Nhập

### 10.1 Panel Intrusion History

Nằm trong control panel bên phải, hiển thị:

```
📜 Intrusion History
┌────────────────────────────────────────────┐
│ 2026-03-10 14:30:25  🚨 2 intruder(s)  🖼️ View │
│ 2026-03-10 14:28:10  🚨 1 intruder(s)  🖼️ View │
│ 2026-03-10 14:25:33  🚨 1 intruder(s)  🖼️ View │
└────────────────────────────────────────────┘
  [🔄 Refresh]  [🗑️ Clear All]
```

### 10.2 Xem ảnh xâm nhập

- Nhấn **"🖼️ View"** bên cạnh mỗi entry → mở ảnh trong tab mới
- Ảnh có đầy đủ bounding box, foot-point, virtual fence tại thời điểm xâm nhập

### 10.3 Quản lý log

- **"🔄 Refresh"**: cập nhật danh sách log mới nhất
- **"🗑️ Clear All"**: xóa toàn bộ lịch sử (cần xác nhận)
- Log tự động **refresh** khi có xâm nhập mới
- Tối đa **500 ảnh** được lưu, ảnh cũ nhất tự động xóa

### 10.4 Vị trí file trên máy

```
server/intrusion_logs/
├── intrusion_log.json          ← Toàn bộ log dạng JSON
├── intrusion_20260310_143025.jpg   ← Ảnh xâm nhập
├── intrusion_20260310_142810.jpg
└── ...
```

---

## 11. Sử Dụng API

Bạn có thể dùng API trực tiếp (Postman, curl, hoặc code):

### Lấy trạng thái hệ thống

```bash
curl http://localhost:5000/api/status
```

Response:
```json
{
    "server": "running",
    "esp32_connected": true,
    "person_count": 2,
    "intrusion_count": 1,
    "fence_active": true,
    "auto_alert_enabled": true,
    "yolo_enabled": true,
    "stream_fps": 15.2,
    "detect_fps": 5.3
}
```

### Bật/tắt YOLO

```bash
curl http://localhost:5000/api/yolo/toggle
```

### Đặt Fence bằng API

```bash
curl -X POST http://localhost:5000/api/fence/set \
  -H "Content-Type: application/json" \
  -d '{"points": [[0.1, 0.2], [0.5, 0.2], [0.5, 0.8], [0.1, 0.8]]}'
```

### Lấy lịch sử xâm nhập

```bash
curl http://localhost:5000/api/logs
```

### Chụp ảnh

```bash
curl http://localhost:5000/api/snapshot --output snapshot.jpg
```

---

## 12. Khắc Phục Sự Cố

### ❌ ESP32-CAM không kết nối WiFi

| Triệu chứng | Giải pháp |
|---|---|
| Serial Monitor hiện dấu `.....` liên tục | Kiểm tra SSID và password trong `main.cpp` |
| WiFi connection failed! Restarting... | ESP32 khởi động lại liên tục → sai mật khẩu WiFi hoặc WiFi 5GHz |
| Không thấy IP Address | Đảm bảo WiFi là 2.4GHz, thử đặt gần router hơn |

### ❌ Flask Server không nhận stream từ ESP32

| Triệu chứng | Giải pháp |
|---|---|
| `Không thể kết nối ESP32-CAM` | Kiểm tra IP trong `config.py` khớp với IP trên Serial Monitor |
| `Timeout kết nối` | ESP32 và máy tính phải cùng mạng WiFi |
| Stream nhận được nhưng lag | Giảm quality: trong `main.cpp` thay `jpeg_quality = 12` → `20` |

### ❌ YOLO detection chậm / lag

| Triệu chứng | Giải pháp |
|---|---|
| Detect FPS < 1 | Tăng `YOLO_DETECT_INTERVAL` lên 3-5 trong `config.py` |
| CPU 100% | Dùng máy có ít nhất 4 core CPU |
| Không nhận ra người | Giảm `YOLO_CONFIDENCE` xuống 0.3 |
| Nhận nhầm vật thể khác | Tăng `YOLO_CONFIDENCE` lên 0.6-0.7 |

### ❌ Buzzer không kêu

| Triệu chứng | Giải pháp |
|---|---|
| Nhấn Buzzer ON nhưng không kêu | Kiểm tra nối dây: GPIO 12 → (+), GND → (−) |
| Buzzer kêu rất nhỏ | Dùng Active Buzzer 3.3V thay vì Passive Buzzer |
| `Không thể bật buzzer` trong log | ESP32 mất kết nối, restart ESP32 |

### ❌ Dashboard không hiện video

| Triệu chứng | Giải pháp |
|---|---|
| "Waiting for ESP32-CAM..." | ESP32 chưa sẵn sàng hoặc IP sai |
| Video đen | Camera chưa khởi tạo, thử restart ESP32 |
| Video giật | Giảm `frame_size` trong firmware hoặc tăng `jpeg_quality` |

### ❌ Virtual Fence không hoạt động

| Triệu chứng | Giải pháp |
|---|---|
| Vẽ fence nhưng không detect intruder | Nhấn **"💾 Save Fence"** chưa? Cần save để gửi lên server |
| Fence biến mất khi reload trang | Fence lưu trên RAM server, cần vẽ lại (hoặc server đang chạy thì fence giữ nguyên) |
| Click không thêm điểm | Đã bật **"✏️ Draw Fence"** chưa? Cần ở chế độ Drawing Mode |

### ❌ Không nghe âm thanh cảnh báo trên web

| Triệu chứng | Giải pháp |
|---|---|
| Không có tiếng beep | Trình duyệt chặn autoplay audio → click vào trang 1 lần trước |
| Âm thanh rất nhỏ | Kiểm tra volume hệ thống và volume trình duyệt |

---

## ⚡ Tóm Tắt Nhanh

```
1. Nạp firmware lên ESP32-CAM (PlatformIO → Upload)
2. Ghi lại IP từ Serial Monitor
3. Sửa IP trong server/config.py
4. cd server && pip install -r requirements.txt
5. python app.py
6. Mở http://localhost:5000
7. Vẽ Virtual Fence → Save
8. Hệ thống tự động nhận diện + cảnh báo xâm nhập ✅
```

---

> 🛡️ **SENTINEL EYE** — Mọi thứ bạn cần để bảo vệ không gian an ninh.
