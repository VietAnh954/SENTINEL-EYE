# ============================================================
# Script tạo PDF Báo Cáo Dự Án SENTINEL EYE
# Chạy: python generate_report_pdf.py
# Output: BAO_CAO_DU_AN.pdf
# ============================================================

from fpdf import FPDF
import os

# ===================== CUSTOM PDF CLASS =====================
class ReportPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        # Load font Arial Unicode (Windows)
        font_dir = "C:/Windows/Fonts"
        self.add_font("ArialUni", "", os.path.join(font_dir, "arial.ttf"))
        self.add_font("ArialUni", "B", os.path.join(font_dir, "arialbd.ttf"))
        self.add_font("ArialUni", "I", os.path.join(font_dir, "ariali.ttf"))
        self.add_font("ArialUni", "BI", os.path.join(font_dir, "arialbi.ttf"))
        # Consolas for code
        consolas_path = os.path.join(font_dir, "consola.ttf")
        if os.path.exists(consolas_path):
            self.add_font("Consolas", "", consolas_path)
        else:
            self.add_font("Consolas", "", os.path.join(font_dir, "cour.ttf"))

        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return  # Trang bìa không có header
        self.set_font("ArialUni", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "SENTINEL EYE - Báo Cáo Dự Án Tương Tác Người và Máy", align="L")
        self.cell(0, 8, f"Trang {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 50, 70)
        self.set_line_width(0.5)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("ArialUni", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"SENTINEL EYE © 2026 — Trang {self.page_no()}/{{nb}}", align="C")

    # --- Tiện ích ---
    def chapter_title(self, num, title):
        self.set_font("ArialUni", "B", 16)
        self.set_text_color(200, 50, 70)  # Đỏ
        self.cell(0, 12, f"{num}. {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 50, 70)
        self.set_line_width(0.8)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def sub_title(self, text):
        self.set_font("ArialUni", "B", 13)
        self.set_text_color(50, 50, 100)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("ArialUni", "", 11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 7, text)
        self.ln(2)

    def bold_text(self, text):
        self.set_font("ArialUni", "B", 11)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def bullet(self, text, indent=20):
        self.set_font("ArialUni", "", 11)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.set_x(indent)
        self.cell(5, 7, "\u2022")
        self.multi_cell(0, 7, text)
        self.ln(1)

    def bullet_bold_desc(self, bold_part, desc):
        """Bullet với phần in đậm + mô tả"""
        self.set_x(20)
        self.set_font("ArialUni", "", 11)
        self.set_text_color(30, 30, 30)
        self.cell(5, 7, "\u2022")
        self.set_font("ArialUni", "B", 11)
        self.cell(self.get_string_width(bold_part) + 2, 7, bold_part)
        self.set_font("ArialUni", "", 11)
        self.multi_cell(0, 7, desc)
        self.ln(1)

    def code_block(self, text):
        self.set_font("Consolas", "", 9)
        self.set_fill_color(240, 240, 245)
        self.set_text_color(50, 50, 50)
        self.set_draw_color(200, 200, 210)
        x = self.get_x()
        y = self.get_y()
        lines = text.split("\n")
        block_h = len(lines) * 5.5 + 6
        if y + block_h > 270:
            self.add_page()
            y = self.get_y()
        self.rect(15, y, 180, block_h, style="FD")
        self.set_xy(18, y + 3)
        for line in lines:
            self.cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(18)
        self.ln(4)

    def table(self, headers, rows, col_widths=None):
        """Vẽ bảng đơn giản"""
        if col_widths is None:
            col_widths = [180 / len(headers)] * len(headers)

        # Check page break
        needed_h = (len(rows) + 1) * 9 + 5
        if self.get_y() + needed_h > 270:
            self.add_page()

        # Header row
        self.set_font("ArialUni", "B", 10)
        self.set_fill_color(45, 55, 90)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 9, h, border=1, fill=True, align="C")
        self.ln()

        # Data rows
        self.set_font("ArialUni", "", 10)
        self.set_text_color(30, 30, 30)
        fill = False
        for row in rows:
            if self.get_y() + 9 > 270:
                self.add_page()
            if fill:
                self.set_fill_color(245, 245, 250)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell_text in enumerate(row):
                self.cell(col_widths[i], 9, str(cell_text), border=1, fill=True)
            self.ln()
            fill = not fill
        self.ln(3)

    def info_box(self, text, color=(230, 245, 255)):
        """Hộp thông tin nổi bật"""
        self.set_fill_color(*color)
        self.set_draw_color(100, 150, 200)
        y = self.get_y()
        self.rect(15, y, 180, 12, style="FD")
        self.set_font("ArialUni", "B", 11)
        self.set_text_color(30, 60, 120)
        self.set_xy(20, y + 2.5)
        self.cell(0, 7, text)
        self.set_xy(15, y + 14)
        self.ln(2)


# ===================== TẠO PDF =====================
pdf = ReportPDF()
pdf.alias_nb_pages()

# ==================== TRANG BÌA ====================
pdf.add_page()

# Background header
pdf.set_fill_color(25, 25, 50)
pdf.rect(0, 0, 210, 297, style="F")

# Decorative line
pdf.set_draw_color(200, 50, 70)
pdf.set_line_width(3)
pdf.line(30, 60, 180, 60)

# Title
pdf.set_y(75)
pdf.set_font("ArialUni", "B", 36)
pdf.set_text_color(233, 69, 96)
pdf.cell(0, 20, "SENTINEL EYE", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.set_font("ArialUni", "", 14)
pdf.set_text_color(200, 200, 220)
pdf.cell(0, 10, "AI Virtual Fence System", align="C", new_x="LMARGIN", new_y="NEXT")

# Decorative line
pdf.ln(5)
pdf.set_draw_color(200, 50, 70)
pdf.set_line_width(1)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(15)

# Subtitle
pdf.set_font("ArialUni", "B", 18)
pdf.set_text_color(78, 204, 163)
pdf.cell(0, 12, "BÁO CÁO DỰ ÁN", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)
pdf.set_font("ArialUni", "", 14)
pdf.set_text_color(180, 180, 200)
pdf.cell(0, 10, "Hệ Thống Giám Sát An Ninh Thông Minh", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 10, "với Hàng Rào Ảo AI", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(20)

# Info box
pdf.set_font("ArialUni", "", 12)
pdf.set_text_color(150, 160, 180)
info_lines = [
    "Môn học:  Tương tác Người và Máy (HCI)",
    "",
    "Công nghệ:  ESP32-CAM  •  YOLOv8  •  Flask  •  OpenCV",
    "",
    "Ngày:  Tháng 3 / 2026",
]
for line in info_lines:
    pdf.cell(0, 8, line, align="C", new_x="LMARGIN", new_y="NEXT")

# Bottom decorative
pdf.set_draw_color(200, 50, 70)
pdf.set_line_width(3)
pdf.line(30, 240, 180, 240)

# ==================== MỤC LỤC ====================
pdf.add_page()
pdf.set_fill_color(255, 255, 255)

pdf.set_font("ArialUni", "B", 20)
pdf.set_text_color(200, 50, 70)
pdf.cell(0, 15, "MỤC LỤC", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(200, 50, 70)
pdf.set_line_width(1)
pdf.line(15, pdf.get_y(), 195, pdf.get_y())
pdf.ln(8)

toc_items = [
    ("1", "Tổng Quan Dự Án"),
    ("2", "Kiến Trúc Hệ Thống"),
    ("3", "Phần Cứng — ESP32-CAM Firmware"),
    ("4", "Phần Mềm — Flask Backend Server"),
    ("5", "Nhận Diện Người — YOLOv8"),
    ("6", "Virtual Fence — Hàng Rào Ảo"),
    ("7", "Hệ Thống Cảnh Báo Tự Động"),
    ("8", "Ghi Log Xâm Nhập"),
    ("9", "Web Dashboard"),
    ("10", "API Endpoints"),
    ("11", "Cấu Trúc Thư Mục"),
    ("12", "Công Nghệ Sử Dụng"),
]

for num, title in toc_items:
    pdf.set_font("ArialUni", "B", 12)
    pdf.set_text_color(50, 50, 100)
    pdf.cell(12, 10, num + ".")
    pdf.set_font("ArialUni", "", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")

# ==================== NỘI DUNG ====================

# --- 1. Tổng Quan Dự Án ---
pdf.add_page()
pdf.chapter_title("1", "Tổng Quan Dự Án")

pdf.body_text(
    "SENTINEL EYE là hệ thống giám sát an ninh thông minh kết hợp phần cứng IoT "
    "(ESP32-CAM) và trí tuệ nhân tạo (YOLOv8). Hệ thống được thiết kế cho môn "
    "Tương tác Người và Máy (HCI), tập trung vào khả năng tương tác trực quan "
    "giữa người dùng và hệ thống an ninh."
)

pdf.bold_text("Các chức năng chính:")
pdf.bullet("Stream video trực tiếp từ camera ESP32-CAM qua WiFi")
pdf.bullet("Nhận diện người trong video bằng mô hình YOLOv8 (deep learning)")
pdf.bullet("Thiết lập vùng cấm (Virtual Fence) bằng cách vẽ polygon trên giao diện web")
pdf.bullet("Phát hiện xâm nhập khi có người bước vào vùng cấm")
pdf.bullet("Tự động cảnh báo bằng còi buzzer trên ESP32 + cảnh báo âm thanh/hình ảnh trên web")
pdf.bullet("Ghi log lịch sử xâm nhập kèm ảnh chụp tự động")

# --- 2. Kiến Trúc Hệ Thống ---
pdf.add_page()
pdf.chapter_title("2", "Kiến Trúc Hệ Thống")

pdf.body_text(
    "Hệ thống hoạt động theo mô hình 3 lớp: ESP32-CAM (phần cứng IoT) giao tiếp "
    "với Flask Server (backend Python) qua WiFi/HTTP, và Flask Server phục vụ "
    "Web Dashboard (frontend) cho người dùng qua trình duyệt web."
)

pdf.sub_title("Sơ đồ kiến trúc")
pdf.code_block(
    "ESP32-CAM              Flask Server              Web Browser\n"
    "(Phan cung)            (Python Backend)           (Dashboard)\n"
    "                                                             \n"
    "  Camera OV2640   -->   MJPEG Stream Reader  -->  Live Video \n"
    "  Buzzer GPIO12   <--   YOLOv8 Detection     -->  Detections \n"
    "  WiFi HTTP API   <--   Virtual Fence Logic  -->  Drawing UI \n"
    "  Status JSON     -->   Alert System         -->  Alert UI   \n"
    "                        Intrusion Logging     -->  Log History"
)

pdf.sub_title("Luồng hoạt động")
pdf.bullet("ESP32-CAM stream video MJPEG qua endpoint /stream")
pdf.bullet("Flask Server đọc stream, lưu frame vào bộ nhớ")
pdf.bullet("Thread YOLO detection phân tích frame, phát hiện người")
pdf.bullet("Kiểm tra foot-point của mỗi người có nằm trong polygon vùng cấm không")
pdf.bullet("Nếu có xâm nhập: tự động bật buzzer + lưu ảnh + ghi log")
pdf.bullet("Web Dashboard hiển thị video đã vẽ bounding box + cảnh báo trực quan")

# --- 3. Phần Cứng ---
pdf.add_page()
pdf.chapter_title("3", "Phần Cứng — ESP32-CAM Firmware")

pdf.info_box("File: HCI_Camera_Test/src/main.cpp  |  Platform: PlatformIO + Arduino")

pdf.sub_title("3.1 Cấu hình phần cứng")
pdf.table(
    ["Thành phần", "Chi tiết"],
    [
        ["Board", "AI-Thinker ESP32-CAM"],
        ["Camera", "OV2640 (VGA 640x480 / QVGA 320x240)"],
        ["Buzzer", "Active Buzzer - GPIO 12 + GND"],
        ["WiFi", "2.4GHz, SSID/Password trong code"],
    ],
    [50, 130]
)

pdf.sub_title("3.2 Các endpoint HTTP trên ESP32")
pdf.table(
    ["Endpoint", "Method", "Mô tả"],
    [
        ["/", "GET", "Trang Control Panel"],
        ["/stream", "GET", "MJPEG video stream liên tục"],
        ["/capture", "GET", "Chụp 1 ảnh JPEG"],
        ["/buzzer/on", "GET", "Bật còi buzzer"],
        ["/buzzer/off", "GET", "Tắt còi buzzer"],
        ["/status", "GET", "Trạng thái JSON (IP, RSSI, buzzer...)"],
    ],
    [40, 25, 115]
)

pdf.sub_title("3.3 Tính năng firmware")
pdf.bullet("Khởi tạo camera với cấu hình tối ưu (độ sáng, tương phản, cân bằng trắng)")
pdf.bullet("CORS headers cho phép Flask server gọi API cross-origin")
pdf.bullet("Tự động kết nối lại WiFi khi mất kết nối trong loop()")
pdf.bullet("Beep xác nhận khởi động — 2 tiếng beep ngắn khi boot thành công")
pdf.bullet("Double buffer (nếu có PSRAM) để stream mượt hơn")

# --- 4. Phần Mềm ---
pdf.add_page()
pdf.chapter_title("4", "Phần Mềm — Flask Backend Server")

pdf.info_box("File: server/app.py  |  Config: server/config.py")

pdf.sub_title("4.1 Kiến trúc đa luồng (Multi-threading)")
pdf.body_text("Server sử dụng 3 thread chạy song song:")
pdf.table(
    ["Thread", "Chức năng"],
    [
        ["Stream Reader", "Đọc MJPEG stream từ ESP32-CAM, lưu frame vào current_frame"],
        ["YOLO Detection", "Chạy YOLOv8, vẽ bounding box, kiểm tra xâm nhập"],
        ["Flask Main", "Phục vụ Web Dashboard, API endpoints, MJPEG cho browser"],
    ],
    [45, 135]
)

pdf.sub_title("4.2 Xử lý Stream")
pdf.bullet("Đọc MJPEG stream bằng requests.get(stream=True)")
pdf.bullet("Parse JPEG frame từ byte stream (tìm marker FFD8 → FFD9)")
pdf.bullet("Decode bằng OpenCV cv2.imdecode()")
pdf.bullet("Tự động kết nối lại khi mất kết nối (retry mỗi 3 giây)")
pdf.bullet("Tính FPS stream real-time")

pdf.sub_title("4.3 Cấu hình (config.py)")
pdf.table(
    ["Tham số", "Mặc định", "Mô tả"],
    [
        ["ESP32_IP", "192.168.1.113", "Địa chỉ IP của ESP32-CAM"],
        ["SERVER_PORT", "5000", "Port Flask server"],
        ["YOLO_MODEL", "yolov8n.pt", "Model YOLO (nano)"],
        ["YOLO_CONFIDENCE", "0.45", "Ngưỡng tin cậy (0.0 - 1.0)"],
        ["YOLO_DETECT_INTERVAL", "2", "Chạy YOLO mỗi N frame"],
        ["ALERT_COOLDOWN", "3s", "Cooldown giữa 2 lần cảnh báo"],
        ["BUZZER_DURATION", "3s", "Thời gian kêu còi mỗi lần"],
        ["MAX_LOG_IMAGES", "500", "Số ảnh log tối đa"],
    ],
    [50, 35, 95]
)

# --- 5. YOLOv8 ---
pdf.add_page()
pdf.chapter_title("5", "Nhận Diện Người — YOLOv8")

pdf.sub_title("5.1 Model")
pdf.bullet("YOLOv8n (Nano) — phiên bản nhẹ nhất của Ultralytics YOLOv8")
pdf.bullet("Được train sẵn trên COCO dataset (80 class, class 0 = 'person')")
pdf.bullet("Chạy trên CPU (không cần GPU)")
pdf.bullet("File model: yolov8n.pt (~6MB)")

pdf.sub_title("5.2 Quy trình detection")
pdf.code_block(
    "Frame tu ESP32 --> YOLOv8 Inference --> Loc class 'person'\n"
    "  --> Tinh foot-point (trung diem day bounding box)\n"
    "  --> Kiem tra Point-in-Polygon --> Ve bounding box + label"
)

pdf.sub_title("5.3 Kết quả detection")
pdf.body_text("Mỗi người phát hiện được lưu dạng JSON:")
pdf.code_block(
    '{\n'
    '    "bbox": [x1, y1, x2, y2],\n'
    '    "confidence": 0.87,\n'
    '    "foot_point": [320, 450],\n'
    '    "intruding": true\n'
    '}'
)

pdf.sub_title("5.4 Hiển thị trên video")
pdf.table(
    ["Trạng thái", "Bounding Box", "Label", "Foot Point"],
    [
        ["An toàn", "Xanh lá, nét 2px", "Person 87% (nền xanh)", "Cam"],
        ["Xâm nhập", "Đỏ, nét 3px", "INTRUSION 87% (nền đỏ)", "Đỏ"],
    ],
    [35, 45, 60, 40]
)

# --- 6. Virtual Fence ---
pdf.add_page()
pdf.chapter_title("6", "Virtual Fence — Hàng Rào Ảo")

pdf.sub_title("6.1 Nguyên lý")
pdf.bullet("Người dùng vẽ polygon (đa giác) trên giao diện web để định nghĩa vùng cấm")
pdf.bullet("Tọa độ được chuẩn hóa (0.0 - 1.0) để không phụ thuộc vào resolution")
pdf.bullet("Sử dụng thuật toán Ray Casting để kiểm tra điểm trong polygon")

pdf.sub_title("6.2 Ray Casting Algorithm")
pdf.code_block(
    "Ban 1 tia tu diem can kiem tra sang phai vo cuc.\n"
    "Dem so lan tia cat canh polygon:\n"
    "  - So le  -->  diem nam TRONG polygon\n"
    "  - So chan -->  diem nam NGOAI polygon"
)

pdf.sub_title("6.3 Foot-Point")
pdf.bullet("Vị trí 'chân người' = trung điểm cạnh dưới bounding box")
pdf.bullet("foot_x = (x1 + x2) / 2,  foot_y = y2")
pdf.bullet("Dùng foot-point thay vì center-point vì chân người tiếp xúc mặt đất = vị trí thực tế")

pdf.sub_title("6.4 Hiển thị trên video")
pdf.bullet("Vùng cấm: tô đỏ nhạt bán trong suốt (alpha 25%)")
pdf.bullet("Viền: nét đỏ đậm 2px")
pdf.bullet("Các đỉnh (vertex): chấm vàng")
pdf.bullet("Nhãn: 'RESTRICTED ZONE' ở tâm polygon")

# --- 7. Cảnh Báo ---
pdf.add_page()
pdf.chapter_title("7", "Hệ Thống Cảnh Báo Tự Động")

pdf.sub_title("7.1 Cảnh báo phần cứng (Buzzer ESP32)")
pdf.bullet("Khi phát hiện xâm nhập → gửi HTTP request GET /buzzer/on tới ESP32")
pdf.bullet("Sau BUZZER_DURATION_SECONDS (3s) → gửi GET /buzzer/off")
pdf.bullet("Cooldown: tối thiểu ALERT_COOLDOWN_SECONDS (3s) giữa 2 lần cảnh báo")
pdf.bullet("Chạy trên thread riêng để không block detection")

pdf.sub_title("7.2 Cảnh báo trên Dashboard")
pdf.table(
    ["Loại cảnh báo", "Mô tả"],
    [
        ["Alert Banner", "Thanh đỏ nhấp nháy: INTRUSION DETECTED"],
        ["Âm thanh web", "3 tiếng beep (880Hz, Web Audio API)"],
        ["Intrusion Badge", "Badge đỏ hiển thị số người xâm nhập"],
        ["Detection List", "Trạng thái INTRUDING (đỏ) hoặc safe"],
        ["Activity Log", "Ghi nhận sự kiện xâm nhập vào log panel"],
    ],
    [45, 135]
)

pdf.sub_title("7.3 Bật/tắt")
pdf.bullet("Nút 'Auto Alert: ON/OFF' trên Dashboard")
pdf.bullet("API: GET /api/alert/toggle")
pdf.bullet("Nút 'Test Alert' để thử nghiệm buzzer")

# --- 8. Ghi Log ---
pdf.add_page()
pdf.chapter_title("8", "Ghi Log Xâm Nhập")

pdf.sub_title("8.1 Dữ liệu lưu trữ")
pdf.body_text("Mỗi sự kiện xâm nhập lưu:")
pdf.code_block(
    '{\n'
    '    "time": "2026-03-10 14:30:25",\n'
    '    "count": 2,\n'
    '    "image": "intrusion_20260310_143025.jpg"\n'
    '}'
)

pdf.sub_title("8.2 Lưu trữ")
pdf.table(
    ["Loại", "Vị trí", "Mô tả"],
    [
        ["Ảnh JPEG", "intrusion_logs/*.jpg", "Ảnh frame có bounding box"],
        ["Log JSON", "intrusion_log.json", "Danh sách toàn bộ sự kiện"],
        ["RAM", "Biến intrusion_log", "200 entries gần nhất (phục vụ API)"],
    ],
    [30, 55, 95]
)

pdf.sub_title("8.3 Quản lý dung lượng")
pdf.bullet("Tự động xóa ảnh cũ nhất khi vượt quá MAX_LOG_IMAGES (500 ảnh)")
pdf.bullet("Log JSON được load lại khi server khởi động")

pdf.sub_title("8.4 Xem lịch sử")
pdf.bullet("Panel 'Intrusion History' trên Dashboard")
pdf.bullet("Mỗi entry hiển thị: thời gian + số người xâm nhập + link xem ảnh")
pdf.bullet("Nút Refresh và Clear All")

# --- 9. Web Dashboard ---
pdf.add_page()
pdf.chapter_title("9", "Web Dashboard")

pdf.sub_title("9.1 Giao diện")
pdf.body_text("Giao diện web tối (dark theme) chuyên nghiệp gồm các panel:")

pdf.table(
    ["Khu vực", "Mô tả"],
    [
        ["Header", "Logo + trạng thái ESP32 + Person/Intrusion count + FPS"],
        ["Alert Banner", "Thanh cảnh báo đỏ nhấp nháy (ẩn khi không có xâm nhập)"],
        ["Video Panel", "Stream video + bounding box + fence overlay + canvas vẽ"],
        ["System Info", "IP, ESP32 status, RSSI, FPS, Person/Intrusion count"],
        ["AI Detection", "Toggle YOLO ON/OFF + Confidence Threshold slider"],
        ["Detected Persons", "Danh sách người + confidence + trạng thái xâm nhập"],
        ["Virtual Fence", "Draw/Undo/Clear/Save fence + thông tin"],
        ["Controls", "Buzzer ON/OFF + Chụp ảnh + Auto Alert + Test Alert"],
        ["Intrusion History", "Lịch sử xâm nhập với ảnh + Refresh/Clear"],
        ["Activity Log", "Console log sự kiện (max 50 entries)"],
    ],
    [42, 138]
)

pdf.sub_title("9.2 Tính năng tương tác (HCI)")
pdf.bullet_bold_desc("Vẽ fence bằng click: ", "chế độ Drawing Mode với crosshair cursor")
pdf.bullet_bold_desc("Real-time status: ", "auto-refresh mỗi 2 giây")
pdf.bullet_bold_desc("Responsive: ", "hỗ trợ mobile (flex column khi < 900px)")
pdf.bullet_bold_desc("Visual feedback: ", "animation, color coding, badge updates")
pdf.bullet_bold_desc("Audio feedback: ", "beep cảnh báo qua Web Audio API")
pdf.bullet_bold_desc("Canvas overlay: ", "fence hiển thị trên video, resize tự động")

# --- 10. API Endpoints ---
pdf.add_page()
pdf.chapter_title("10", "API Endpoints")

pdf.body_text("Flask Server (http://localhost:5000)")
pdf.table(
    ["Endpoint", "Method", "Mô tả"],
    [
        ["/", "GET", "Web Dashboard"],
        ["/video_feed", "GET", "MJPEG stream (có detection overlay)"],
        ["/api/status", "GET", "Trạng thái toàn hệ thống (JSON)"],
        ["/api/detections", "GET", "Danh sách detection hiện tại"],
        ["/api/yolo/toggle", "GET", "Bật/tắt YOLO detection"],
        ["/api/yolo/confidence/<val>", "GET", "Đặt ngưỡng confidence (0.0-1.0)"],
        ["/api/snapshot", "GET", "Chụp ảnh frame hiện tại"],
        ["/api/fence/set", "POST", "Lưu polygon vùng cấm"],
        ["/api/fence/get", "GET", "Lấy polygon hiện tại"],
        ["/api/fence/clear", "GET", "Xóa polygon"],
        ["/api/alert/toggle", "GET", "Bật/tắt tự động cảnh báo"],
        ["/api/alert/test", "GET", "Test buzzer cảnh báo"],
        ["/api/logs", "GET", "Lấy lịch sử xâm nhập (50 gần nhất)"],
        ["/api/logs/clear", "GET", "Xóa toàn bộ log"],
        ["/api/logs/image/<file>", "GET", "Xem ảnh xâm nhập"],
        ["/api/esp32/buzzer/on", "GET", "Bật buzzer qua ESP32"],
        ["/api/esp32/buzzer/off", "GET", "Tắt buzzer qua ESP32"],
    ],
    [55, 20, 105]
)

# --- 11. Cấu Trúc Thư Mục ---
pdf.add_page()
pdf.chapter_title("11", "Cấu Trúc Thư Mục")

pdf.code_block(
    "HCL/\n"
    "|-- BAO_CAO_DU_AN.pdf\n"
    "|-- HUONG_DAN_SU_DUNG.md\n"
    "|-- yolov8n.pt                  (Model YOLO backup)\n"
    "|-- intrusion_logs/\n"
    "|\n"
    "|-- server/                     (Flask Backend)\n"
    "|   |-- app.py                  (Server chinh ~550 dong)\n"
    "|   |-- config.py               (Cau hinh tap trung)\n"
    "|   |-- requirements.txt        (Python dependencies)\n"
    "|   |-- yolov8n.pt              (Model YOLO)\n"
    "|   |-- intrusion_logs/         (Anh + log xam nhap)\n"
    "|   |   |-- intrusion_log.json\n"
    "|   |   |-- intrusion_*.jpg\n"
    "|   |-- templates/\n"
    "|       |-- index.html          (Web Dashboard ~800 dong)\n"
    "|\n"
    "HCI_Camera_Test/                (PlatformIO Project)\n"
    "|-- platformio.ini\n"
    "|-- src/\n"
    "    |-- main.cpp                (ESP32-CAM Firmware ~330 dong)"
)

# --- 12. Công Nghệ ---
pdf.add_page()
pdf.chapter_title("12", "Công Nghệ Sử Dụng")

pdf.sub_title("Phần cứng")
pdf.table(
    ["Công nghệ", "Mục đích"],
    [
        ["ESP32-CAM (AI-Thinker)", "Camera module + WiFi + GPIO"],
        ["Active Buzzer", "Cảnh báo âm thanh vật lý"],
        ["PlatformIO + Arduino", "Framework lập trình firmware"],
    ],
    [65, 115]
)

pdf.sub_title("Phần mềm Backend")
pdf.table(
    ["Công nghệ", "Version", "Mục đích"],
    [
        ["Python", "3.x", "Ngôn ngữ backend"],
        ["Flask", "3.1.0", "Web framework"],
        ["Flask-CORS", "5.0.1", "Cross-Origin Resource Sharing"],
        ["OpenCV", "4.10.0", "Xử lý ảnh, encode/decode JPEG"],
        ["NumPy", "2.2.3", "Xử lý mảng, tính toán"],
        ["Requests", "2.32.3", "HTTP client (gọi ESP32 API)"],
        ["Ultralytics", "latest", "YOLO detection engine"],
        ["YOLOv8n", "v8 nano", "Model nhận diện đối tượng"],
    ],
    [45, 30, 105]
)

pdf.sub_title("Frontend")
pdf.table(
    ["Công nghệ", "Mục đích"],
    [
        ["HTML5 / CSS3", "Giao diện Dashboard"],
        ["JavaScript (vanilla)", "Logic tương tác, fetch API"],
        ["Canvas API", "Vẽ fence overlay trên video"],
        ["Web Audio API", "Âm thanh cảnh báo trên trình duyệt"],
    ],
    [55, 125]
)

pdf.sub_title("Thuật toán")
pdf.table(
    ["Thuật toán", "Mục đích"],
    [
        ["YOLOv8 (Deep Learning)", "Nhận diện người trong video"],
        ["Ray Casting", "Kiểm tra điểm trong polygon"],
        ["MJPEG Parsing", "Tách frame JPEG từ stream byte"],
        ["Coordinate Normalization", "Chuẩn hóa tọa độ fence (0.0-1.0)"],
    ],
    [60, 120]
)

# --- Trang cuối ---
pdf.add_page()
pdf.set_fill_color(25, 25, 50)
pdf.rect(0, 0, 210, 297, style="F")

pdf.set_y(100)
pdf.set_font("ArialUni", "B", 28)
pdf.set_text_color(233, 69, 96)
pdf.cell(0, 15, "SENTINEL EYE", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.ln(5)
pdf.set_draw_color(200, 50, 70)
pdf.set_line_width(1)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(10)

pdf.set_font("ArialUni", "", 14)
pdf.set_text_color(78, 204, 163)
pdf.cell(0, 10, "Hệ thống giám sát an ninh hoàn chỉnh", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 10, "IoT  +  AI  +  Web", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.set_font("ArialUni", "I", 12)
pdf.set_text_color(150, 160, 180)
pdf.cell(0, 10, "Dự án Tương tác Người và Máy — 2026", align="C", new_x="LMARGIN", new_y="NEXT")

# ===================== XUẤT FILE =====================
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BAO_CAO_DU_AN.pdf")
pdf.output(output_path)
print(f"\n{'='*50}")
print(f"  PDF đã tạo thành công!")
print(f"  File: {output_path}")
print(f"{'='*50}\n")
