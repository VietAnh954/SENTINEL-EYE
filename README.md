# 🛡️ SENTINEL-EYE

> **AI-Powered Smart Security Surveillance System with Virtual Fence**  
> Kết hợp IoT (ESP32-CAM) và Trí tuệ Nhân tạo (YOLOv8) để giám sát và cảnh báo an ninh thời gian thực.

---

## 🌟 Tính Năng Nổi Bật

- 📹 **Live Video Streaming**: Truyền phát video MJPEG trực tiếp từ camera ESP32-CAM qua WiFi.
- 🧠 **AI Detection**: Nhận diện người theo thời gian thực sử dụng mô hình YOLOv8.
- 🚧 **Virtual Fence (Hàng rào ảo)**: Cho phép vẽ các vùng cấm đa giác tùy chỉnh trực tiếp trên giao diện web.
- 🚨 **Hệ Thống Cảnh Báo**: Tự động kích hoạt còi báo động (Active Buzzer trên GPIO 12 của ESP32) cùng âm thanh/hình ảnh trên Dashboard khi có xâm nhập.
- 📝 **Intrusion Logging**: Tự động ghi lại nhật ký xâm nhập và chụp ảnh bằng chứng lưu trữ an toàn.
- 📊 **Web Dashboard**: Giao diện điều khiển trực quan, hiện đại và thân thiện với người dùng.

---

## 🏗️ Kiến Trúc Hệ Thống

```text
┌─────────────────────┐    WiFi/HTTP     ┌──────────────────────┐    HTTP     ┌──────────────┐
│   ESP32-CAM         │ ──────────────▶  │   Flask Server       │ ─────────▶ │  Web Browser │
│   (Phần cứng)       │                  │   (Python Backend)   │            │  (Dashboard) │
│                     │ ◀──────────────  │                      │            │              │
│  • Camera OV2640/   │  Buzzer control   │  • MJPEG Stream      │            │  • Live View │
│    OV3660           │                  │  • YOLOv8 Detection  │            │  • Controls  │
│  • Buzzer GPIO 12   │                  │  • Virtual Fence     │            │  • Alerts    │
│  • PlatformIO C++   │                  │  • Alert System      │            │  • Logs      │
└─────────────────────┘                  └──────────────────────┘            └──────────────┘
```

---

## 📁 Cấu Trúc Dự Án

```
SENTINEL-EYE/
├── HCL/
│   ├── HCI_Camera_Test/      # Firmware mã nguồn C++/PlatformIO cho ESP32-CAM
│   │   ├── src/main.cpp      # Code điều khiển camera và buzzer
│   │   └── platformio.ini    # Cấu hình PlatformIO
│   ├── server/               # Flask backend server & giao diện Web
│   │   ├── app.py            # Main server, luồng xử lý AI & API
│   │   ├── config.py         # File cấu hình camera, model, cảnh báo
│   │   ├── templates/        # Giao diện HTML Dashboard
│   │   └── requirements.txt  # Danh sách thư viện Python cần thiết
│   ├── fine_tuning/          # Scripts thu thập dữ liệu & fine-tune mô hình YOLO
│   ├── BÁO_CÁO_DỰ_ÁN.md      # Báo cáo chi tiết kiến trúc & triển khai
│   └── HƯỚNG_DẪN_SỬ_DỤNG.md  # Hướng dẫn chi tiết từng bước lắp đặt & sử dụng
└── README.md
```

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Nạp Firmware cho ESP32-CAM
1. Mở thư mục `HCL/HCI_Camera_Test` trong **VS Code** với extension **PlatformIO**.
2. Cập nhật thông tin WiFi (`WIFI_SSID`, `WIFI_PASS`) trong `src/main.cpp`.
3. Kết nối ESP32-CAM qua mạch nạp USB-TTL và bấm **Upload**.

### 2. Khởi Chạy Python Server
1. Mở terminal tại thư mục `HCL/server`:
   ```bash
   cd HCL/server
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Cấu hình IP của ESP32-CAM trong file `config.py` (hoặc cấu hình trực tiếp trên Web Dashboard).
3. Tải trọng số mô hình YOLO (ví dụ `yolov8n.pt` hoặc model đã huấn luyện) đặt vào thư mục `server/`.
4. Chạy server:
   ```bash
   python app.py
   ```
5. Mở trình duyệt và truy cập: `http://localhost:5000`

---

## 📖 Tài Liệu Tham Khảo
- [Báo Cáo Dự Án](HCL/B%C3%81O_C%C3%81O_D%E1%BB%B0_%C3%81N.md)
- [Hướng Dẫn Sử Dụng Chi Tiết](HCL/H%C6%AF%E1%BB%9ANG_D%E1%BA%AAN_S%E1%BB%AC_D%E1%BB%A4NG.md)
- [Hướng Dẫn Fine-Tuning YOLO](HCL/fine_tuning/HUONG_DAN_FINE_TUNING.md)
