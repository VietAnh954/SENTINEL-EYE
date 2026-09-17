# ============================================================
# SENTINEL EYE - Flask Backend Server (Step 5: Intrusion Detection)
# Chức năng: MJPEG stream + YOLOv8 + Virtual Fence + Point-in-Polygon
# ============================================================

from flask import Flask, Response, render_template, jsonify, request
from flask_cors import CORS
import cv2
import numpy as np
import requests
import threading
import time
import os
import sys
import json
from datetime import datetime

# Thư viện gửi Email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# Thêm thư mục chứa app.py vào sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

# Import YOLO
from ultralytics import YOLO

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
CORS(app)

# ===================== GLOBAL STATE =====================
# Frame mới nhất từ ESP32-CAM (raw, chưa vẽ gì)
current_frame = None
# Frame đã vẽ detection (có bounding box)
detected_frame = None
frame_lock = threading.Lock()

# YOLO detection results
detections = []           # List of {"bbox": [x1,y1,x2,y2], "confidence": float, "foot_point": [x,y]}
detections_lock = threading.Lock()

# Trạng thái
esp32_connected = False
stream_fps = 0
detect_fps = 0
yolo_enabled = True       # Bật/tắt YOLO detection
person_count = 0          # Số người phát hiện được trong frame hiện tại

# Virtual Fence (polygon) - tọa độ chuẩn hóa (0.0 - 1.0)
# Mỗi điểm: [x_norm, y_norm] với x_norm = x_pixel / frame_width
fence_polygon = []        # List of [x_norm, y_norm]
fence_lock = threading.Lock()

# Intrusion tracking
intrusion_count = 0       # Số người đang xâm nhập vùng cấm

# Alert system
alert_active = False       # Đang trong trạng thái cảnh báo?
last_alert_time = 0        # Timestamp lần cảnh báo gần nhất
auto_alert_enabled = True  # Bật/tắt tự động cảnh báo

# Intrusion log
intrusion_log = []         # List of {"time": str, "count": int, "image": str or None}
log_lock = threading.Lock()

# ===================== POINT-IN-POLYGON =====================
def point_in_polygon(px, py, polygon):
    """
    Ray Casting algorithm: kiểm tra điểm (px, py) nằm trong polygon hay không.
    polygon: list of [x, y] (tọa độ cùng hệ với px, py)
    Trả về True nếu điểm nằm trong polygon.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# ===================== YOLO MODELS (DUAL) =====================
# Model 1: Phát hiện TẤT CẢ người
print(f"[MODEL 1] Đang tải model phát hiện người: {config.YOLO_MODEL}...")
yolo_model = YOLO(config.YOLO_MODEL)
print(f"[MODEL 1] Loaded thành công!")

# Model 2: Nhận diện chủ nhà
owner_model = None
if config.OWNER_DETECT_ENABLED:
    print(f"[MODEL 2] Đang tải model nhận diện chủ nhà: {config.OWNER_MODEL}...")
    try:
        owner_model = YOLO(config.OWNER_MODEL)
        print(f"[MODEL 2] Loaded thành công! Chế độ DUAL MODEL đã bật.")
    except Exception as e:
        print(f"[MODEL 2] Lỗi tải model: {e}")
        print(f"[MODEL 2] Tiếp tục chạy với model đơn (không nhận diện chủ nhà).")
        owner_model = None

# ===================== STREAM READER =====================
def read_esp32_stream():
    """
    Đọc MJPEG stream từ ESP32-CAM liên tục.
    Lưu frame mới nhất vào current_frame.
    """
    global current_frame, esp32_connected, stream_fps

    while True:
        try:
            print(f"[STREAM] Đang kết nối đến ESP32-CAM: {config.ESP32_STREAM_URL}")
            response = requests.get(config.ESP32_STREAM_URL, stream=True, timeout=10)
            esp32_connected = True
            print("[STREAM] Kết nối thành công! Đang nhận stream...")

            bytes_data = b''
            frame_count = 0
            fps_start_time = time.time()

            # Dùng chunk_size nhỏ (1024 byte) để lấy data ngay lập tức không bị chờ đợi khối to 64KB!
            for chunk in response.iter_content(chunk_size=1024):
                bytes_data += chunk
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')

                if a != -1 and b != -1:
                    jpg_data = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]

                    np_arr = np.frombuffer(jpg_data, dtype=np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                    if frame is not None:
                        h, w = frame.shape[:2]
                        if w < 640:
                            frame = cv2.resize(frame, (640, int(640 * h / w)))

                        with frame_lock:
                            current_frame = frame

                        frame_count += 1
                        elapsed = time.time() - fps_start_time
                        if elapsed >= 2.0:
                            stream_fps = round(frame_count / elapsed, 1)
                            frame_count = 0
                            fps_start_time = time.time()

        except requests.exceptions.ConnectionError:
            esp32_connected = False
            print(f"[STREAM] Không thể kết nối ESP32-CAM tại {config.ESP32_IP}")
            print("[STREAM] Kiểm tra: 1) ESP32 đã bật? 2) Cùng WiFi? 3) IP đúng chưa?")
        except requests.exceptions.Timeout:
            esp32_connected = False
            print("[STREAM] Timeout kết nối ESP32-CAM")
        except Exception as e:
            esp32_connected = False
            print(f"[STREAM] Lỗi: {e}")

        print("[STREAM] Thử kết nối lại sau 3 giây...")
        time.sleep(3)


def compute_iou(box1, box2):
    """
    Tính IoU (Intersection over Union) giữa 2 bounding box.
    box format: [x1, y1, x2, y2]
    """
    xa = max(box1[0], box2[0])
    ya = max(box1[1], box2[1])
    xb = min(box1[2], box2[2])
    yb = min(box1[3], box2[3])

    inter = max(0, xb - xa) * max(0, yb - ya)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0


def detect_owners_in_frame(frame):
    """
    Chạy sentinel_eye model trên TOÀN BỘ frame gốc.
    Trả về danh sách bounding box của chủ nhà được nhận diện.
    """
    if owner_model is None or not config.OWNER_DETECT_ENABLED:
        return []

    try:
        results = owner_model(frame, conf=config.OWNER_CONFIDENCE, imgsz=320, verbose=False)
        owner_boxes = []
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    owner_boxes.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(conf, 2)
                    })
        return owner_boxes
    except Exception as e:
        return []


def match_owner_to_person(person_bbox, owner_boxes, iou_threshold=0.3):
    """
    Kiểm tra người này có khớp với bất kỳ owner detection nào không.
    So khớp bằng IoU (Intersection over Union).
    Trả về (is_owner, owner_confidence).
    """
    best_iou = 0
    best_conf = 0

    for owner in owner_boxes:
        iou = compute_iou(person_bbox, owner["bbox"])
        if iou > best_iou:
            best_iou = iou
            best_conf = owner["confidence"]

    if best_iou >= iou_threshold:
        return True, best_conf
    return False, 0.0


def draw_detections_and_fence(display_frame):
    # Vẽ detections và fence lên frame cung cấp (tách biệt stream và yolo)
    count = 0
    intruders = 0
    
    with detections_lock:
        current_dets = list(detections)
        
    for d in current_dets:
        count += 1
        x1, y1, x2, y2 = d["bbox"]
        conf = d["confidence"]
        foot_x, foot_y = d["foot_point"]
        is_intruding = d["intruding"]
        is_owner = d.get("is_owner", False)

        if is_owner:
            # Chủ nhà → Xanh dương, không bao giờ tính là xâm nhập
            color_box = (255, 200, 0)       # Xanh dương sáng
            color_label_bg = (255, 200, 0)
            color_label_text = (0, 0, 0)
            label = f"Owner {conf:.0%} | {d.get('distance', 0.0)}m"
            thickness = 2
        elif is_intruding:
            # Người lạ trong vùng cấm → ĐỎ
            intruders += 1
            color_box = (0, 0, 255)
            color_label_bg = (0, 0, 255)
            color_label_text = (255, 255, 255)
            label = f"STRANGER! {conf:.0%} | {d.get('distance', 0.0)}m"
            thickness = 3
        else:
            # Người lạ ngoài vùng cấm → Xanh lá
            color_box = (0, 255, 0)
            color_label_bg = (0, 255, 0)
            color_label_text = (0, 0, 0)
            label = f"Person {conf:.0%} | {d.get('distance', 0.0)}m"
            thickness = 2

        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color_box, thickness)
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(display_frame, (x1, y1 - label_size[1] - 10),
                      (x1 + label_size[0] + 5, y1), color_label_bg, -1)
        cv2.putText(display_frame, label, (x1 + 2, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_label_text, 2)

        foot_color = (0, 0, 255) if is_intruding else (0, 165, 255)
        if is_owner:
            foot_color = (255, 200, 0)
        cv2.circle(display_frame, (foot_x, foot_y), 6, foot_color, -1)
        cv2.circle(display_frame, (foot_x, foot_y), 8, foot_color, 2)

    with fence_lock:
        poly = list(fence_polygon)

    if len(poly) >= 3:
        h, w = display_frame.shape[:2]
        pts_px = np.array([[int(p[0] * w), int(p[1] * h)] for p in poly], dtype=np.int32)
        overlay = display_frame.copy()
        cv2.fillPoly(overlay, [pts_px], (0, 0, 180))
        cv2.addWeighted(overlay, 0.25, display_frame, 0.75, 0, display_frame)
        cv2.polylines(display_frame, [pts_px], isClosed=True, color=(0, 0, 255), thickness=2)
        for pt in pts_px:
            cv2.circle(display_frame, tuple(pt), 4, (0, 255, 255), -1)
        cx = int(np.mean(pts_px[:, 0]))
        cy = int(np.mean(pts_px[:, 1]))
        cv2.putText(display_frame, "RESTRICTED ZONE", (cx - 80, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    if intruders > 0:
        bar_color = (0, 0, 200)
        cv2.rectangle(display_frame, (0, 0), (640, 6), bar_color, -1)
    
    return display_frame

# ===================== YOLO DETECTION THREAD =====================
def yolo_detection_loop():
    """
    Thread riêng chạy YOLO detection trên frame hiện tại.
    Kết quả lưu vào detected_frame (frame đã vẽ) và detections (tọa độ).
    """
    global detected_frame, detections, detect_fps, person_count, intrusion_count

    frame_counter = 0
    detect_count = 0
    detect_fps_start = time.time()

    while True:
        if not yolo_enabled:
            time.sleep(0.1)
            continue

        # Lấy frame hiện tại
        with frame_lock:
            frame = current_frame.copy() if current_frame is not None else None

        if frame is None:
            time.sleep(0.05)
            continue

        frame_counter += 1

        # Chỉ chạy YOLO mỗi N frame (để giảm tải CPU)
        if frame_counter % config.YOLO_DETECT_INTERVAL != 0:
            time.sleep(0.01)
            continue

        try:
            # Chạy YOLOv8 detection
            results = yolo_model(frame, conf=config.YOLO_CONFIDENCE, imgsz=320, verbose=False)

            new_detections = []
            count = 0

            # Chạy sentinel_eye trên toàn bộ frame 1 lần (không crop từng người)
            owner_boxes = detect_owners_in_frame(frame)

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    cls_id = int(box.cls[0])

                    if cls_id != config.YOLO_PERSON_CLASS_ID:
                        continue

                    count += 1
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # TÍNH KHOẢNG CÁCH
                    bbox_height = y2 - y1
                    distance = 0.0
                    if bbox_height > 0:
                        distance = (config.KNOWN_PERSON_HEIGHT_M * config.FOCAL_LENGTH) / bbox_height

                    foot_x = (x1 + x2) // 2
                    foot_y = y2

                    is_intruding = False
                    with fence_lock:
                        poly = list(fence_polygon)
                    if len(poly) >= 3:
                        h_frame, w_frame = frame.shape[:2]
                        foot_norm_x = foot_x / w_frame
                        foot_norm_y = foot_y / h_frame
                        is_intruding = point_in_polygon(foot_norm_x, foot_norm_y, poly)

                    # So khớp với owner detections bằng IoU
                    is_owner, owner_conf = match_owner_to_person([x1, y1, x2, y2], owner_boxes)

                    # Nếu là chủ nhà → không tính là xâm nhập
                    if is_owner:
                        is_intruding = False

                    new_detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(conf, 2),
                        "foot_point": [foot_x, foot_y],
                        "intruding": is_intruding,
                        "is_owner": is_owner,
                        "owner_conf": owner_conf,
                        "distance": round(distance, 2)
                    })

            # Chỉ đếm người lạ xâm nhập (không tính chủ nhà)
            intruders = sum(1 for d in new_detections if d['intruding'] and not d.get('is_owner', False))

            if intruders > 0 and auto_alert_enabled:
                trigger_frame = draw_detections_and_fence(frame.copy())
                trigger_intrusion_alert(trigger_frame, intruders)

            with detections_lock:
                detections = new_detections
            person_count = count
            intrusion_count = intruders

            detect_count += 1
            elapsed = time.time() - detect_fps_start
            if elapsed >= 2.0:
                detect_fps = round(detect_count / elapsed, 1)
                detect_count = 0
                detect_fps_start = time.time()

        except Exception as e:
            print(f"[YOLO] Lỗi detection: {e}")
            time.sleep(0.1)

        time.sleep(0.01)


# ===================== INTRUSION ALERT & LOGGING =====================
def trigger_intrusion_alert(frame, intruder_count):
    """
    Tự động bật buzzer và khởi động chụp burst khi phát hiện xâm nhập.
    - Chụp 5 ảnh trong 5 giây đầu tiên
    - Gửi email đính kèm tất cả 5 ảnh
    - Cooldown 30 giây trước khi kích hoạt lại
    """
    global last_alert_time, alert_active

    now = time.time()
    if now - last_alert_time < config.ALERT_COOLDOWN_SECONDS:
        return  # Còn trong cooldown

    last_alert_time = now
    alert_active = True
    timestamp_str_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ALERT] Phát hiện {intruder_count} người xâm nhập lúc {timestamp_str_human}! Kích hoạt cảnh báo.")
    print(f"[ALERT] Bắt đầu chụp {config.BURST_CAPTURE_COUNT} ảnh trong {config.BURST_CAPTURE_COUNT * config.BURST_CAPTURE_INTERVAL}s...")

    # Tự động bật buzzer trên ESP32
    threading.Thread(target=auto_buzzer_alert, daemon=True).start()

    # Chụp burst 5 ảnh + gửi email (chạy trên thread riêng để không block detection)
    threading.Thread(
        target=burst_capture_and_email,
        args=(intruder_count, timestamp_str_human),
        daemon=True
    ).start()


def burst_capture_and_email(intruder_count, timestamp_str_human):
    """
    Chụp liên tục 5 ảnh trong 5 giây (mỗi giây 1 ảnh).
    Sau khi chụp xong, gửi 1 email đính kèm tất cả ảnh.
    """
    global alert_active

    image_paths = []
    image_filenames = []
    os.makedirs(config.LOG_DIR, exist_ok=True)

    for i in range(config.BURST_CAPTURE_COUNT):
        try:
            # Lấy frame hiện tại
            with frame_lock:
                frame = current_frame.copy() if current_frame is not None else None

            if frame is not None:
                # Vẽ detections + fence overlay lên ảnh
                display_frame = draw_detections_and_fence(frame)

                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"intrusion_{timestamp_str}_{i+1}.jpg"
                image_path = os.path.join(config.LOG_DIR, image_filename)
                cv2.imwrite(image_path, display_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

                image_paths.append(image_path)
                image_filenames.append(image_filename)
                print(f"[BURST] Ảnh {i+1}/{config.BURST_CAPTURE_COUNT} đã chụp: {image_filename}")
            else:
                print(f"[BURST] Ảnh {i+1}/{config.BURST_CAPTURE_COUNT}: Không có frame!")

        except Exception as e:
            print(f"[BURST] Lỗi chụp ảnh {i+1}: {e}")

        # Chờ trước khi chụp ảnh tiếp (trừ ảnh cuối cùng)
        if i < config.BURST_CAPTURE_COUNT - 1:
            time.sleep(config.BURST_CAPTURE_INTERVAL)

    print(f"[BURST] Hoàn tất chụp {len(image_paths)}/{config.BURST_CAPTURE_COUNT} ảnh.")

    # Giới hạn số ảnh log
    cleanup_log_images()

    # Lưu event log (dùng ảnh đầu tiên làm thumbnail)
    first_image = image_filenames[0] if image_filenames else None
    log_entry = {
        "time": timestamp_str_human,
        "count": intruder_count,
        "image": first_image,
        "burst_images": image_filenames
    }
    with log_lock:
        intrusion_log.append(log_entry)
        if len(intrusion_log) > 200:
            intrusion_log.pop(0)

    # Lưu log ra file JSON
    save_log_to_file()

    # Gửi Email đính kèm tất cả ảnh burst
    if image_paths and config.EMAIL_ALERT_ENABLED:
        send_intrusion_email(image_paths, intruder_count, timestamp_str_human)

    alert_active = False


def auto_buzzer_alert():
    """Bật buzzer trên ESP32, chờ một khoảng rồi tắt."""
    try:
        requests.get(config.ESP32_BUZZER_ON_URL, timeout=2)
        print(f"[ALERT] Buzzer ON (tự động {config.BUZZER_DURATION_SECONDS}s)")
    except Exception as e:
        print(f"[ALERT] Không thể bật buzzer: {e}")

    time.sleep(config.BUZZER_DURATION_SECONDS)

    try:
        requests.get(config.ESP32_BUZZER_OFF_URL, timeout=2)
        print("[ALERT] Buzzer OFF (tự động)")
    except Exception as e:
        print(f"[ALERT] Không thể tắt buzzer: {e}")


def cleanup_log_images():
    """Xóa ảnh log cũ nếu vượt quá MAX_LOG_IMAGES."""
    try:
        log_dir = config.LOG_DIR
        images = sorted([
            f for f in os.listdir(log_dir)
            if f.startswith("intrusion_") and f.endswith(".jpg")
        ])
        while len(images) > config.MAX_LOG_IMAGES:
            oldest = images.pop(0)
            os.remove(os.path.join(log_dir, oldest))
            print(f"[LOG] Đã xóa ảnh cũ: {oldest}")
    except Exception as e:
        print(f"[LOG] Lỗi cleanup: {e}")


def save_log_to_file():
    """Lưu intrusion log ra file JSON."""
    try:
        log_path = os.path.join(config.LOG_DIR, "intrusion_log.json")
        with log_lock:
            data = list(intrusion_log)
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[LOG] Lỗi lưu log file: {e}")


def load_log_from_file():
    """Đọc intrusion log từ file JSON khi server khởi động."""
    global intrusion_log
    try:
        log_path = os.path.join(config.LOG_DIR, "intrusion_log.json")
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with log_lock:
                intrusion_log = data
            print(f"[LOG] Đã tải {len(data)} intrusion log entries.")
    except Exception as e:
        print(f"[LOG] Lỗi đọc log file: {e}")

# ===================== EMAIL THREAD =====================
def send_intrusion_email(image_paths, intruder_count, timestamp):
    """
    Gửi email cảnh báo kèm nhiều ảnh chụp kẻ xâm nhập (burst capture).
    image_paths: list các đường dẫn ảnh JPEG
    """
    num_images = len(image_paths)
    print(f"[EMAIL] Chuẩn bị gửi email cảnh báo với {num_images} ảnh đính kèm...")
    try:
        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = config.RECEIVER_EMAIL
        msg['Subject'] = f"🚨 CẢNH BÁO AN NINH MỨC ĐỎ - Sentinel Eye [{timestamp}]"

        # Nội dung bằng chữ
        body_text = (
            f"CẢNH BÁO: Phát hiện {intruder_count} người lạ leo vào vùng cấm!\n\n"
            f"Thời gian: {timestamp}\n"
            f"Camera ID: Sentinel-Eye-ESP32\n"
            f"Số ảnh đính kèm: {num_images} ảnh (chụp liên tục trong 5 giây)\n\n"
            f"Vui lòng kiểm tra camera hoặc báo ngay cho bảo vệ tòa nhà.\n"
            f"Các hình chụp tự động đã được đính kèm bên dưới email này."
        )
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

        # Đính kèm tất cả ảnh burst
        attached_count = 0
        for image_path in image_paths:
            if os.path.exists(image_path):
                with open(image_path, "rb") as image_file:
                    img_data = image_file.read()
                    image_mime = MIMEImage(img_data, name=os.path.basename(image_path))
                    msg.attach(image_mime)
                    attached_count += 1

        print(f"[EMAIL] Đã đính kèm {attached_count}/{num_images} ảnh vào email.")

        # Gửi vào SMTP Server
        server = smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT)
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[EMAIL] GỬI EMAIL THÀNH CÔNG TỚI: {config.RECEIVER_EMAIL} ({attached_count} ảnh)!")
    except Exception as e:
        print(f"[EMAIL FAIL] Lỗi nghiêm trọng khi gửi mail. Hãy kiểm tra App Password! Chi tiết: {e}")

# ===================== MJPEG GENERATOR =====================
def generate_mjpeg():
    """
    Phát MJPEG stream: frame đã vẽ detection nếu YOLO bật, 
    hoặc frame raw nếu YOLO tắt.
    Chỉ gửi frame mới để không lấn át băng thông, gây delay.
    """
    last_sent_frame = None
    while True:
        frame = None
        with frame_lock:
            if current_frame is not None:
                if id(current_frame) != last_sent_frame:
                    frame = current_frame.copy()
                    last_sent_frame = id(current_frame)

        if frame is not None:
            if yolo_enabled:
                frame = draw_detections_and_fence(frame)

            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       jpeg.tobytes() +
                       b'\r\n')
        else:
            time.sleep(0.01)

        # Chờ frame trống (nếu chưa có thiết bị ESP32 boot)
        if current_frame is None and last_sent_frame is None:
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank, "Waiting for ESP32-CAM...", (100, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(blank, f"Target: {config.ESP32_IP}", (150, 270),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            ret, jpeg = cv2.imencode('.jpg', blank)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       jpeg.tobytes() +
                       b'\r\n')
            last_sent_frame = blank
            time.sleep(1.0) # Không ping blank image liên tục


# ===================== FLASK ROUTES =====================

@app.route('/')
def index():
    return render_template('index.html',
                           esp32_ip=config.ESP32_IP,
                           server_port=config.SERVER_PORT)


@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def api_status():
    esp32_status = None
    try:
        r = requests.get(config.ESP32_STATUS_URL, timeout=2)
        esp32_status = r.json()
    except:
        pass

    with detections_lock:
        current_detections = list(detections)

    with fence_lock:
        fence_active = len(fence_polygon) >= 3

    return jsonify({
        "server": "running",
        "esp32_connected": esp32_connected,
        "esp32_ip": config.ESP32_IP,
        "stream_fps": stream_fps,
        "detect_fps": detect_fps,
        "yolo_enabled": yolo_enabled,
        "person_count": person_count,
        "intrusion_count": intrusion_count,
        "fence_active": fence_active,
        "alert_active": alert_active,
        "auto_alert_enabled": auto_alert_enabled,
        "detections": current_detections,
        "esp32_status": esp32_status
    })


@app.route('/api/yolo/toggle')
def api_yolo_toggle():
    """Bật/tắt YOLO detection"""
    global yolo_enabled
    yolo_enabled = not yolo_enabled
    state = "ON" if yolo_enabled else "OFF"
    print(f"[YOLO] Detection {state}")
    return jsonify({"yolo_enabled": yolo_enabled})


@app.route('/api/yolo/confidence/<float:value>')
def api_yolo_confidence(value):
    """Thay đổi ngưỡng confidence"""
    if 0.0 <= value <= 1.0:
        config.YOLO_CONFIDENCE = value
        print(f"[YOLO] Confidence threshold -> {value}")
        return jsonify({"confidence": value})
    return jsonify({"error": "Value must be 0.0 - 1.0"}), 400


@app.route('/api/detections')
def api_detections():
    """Lấy kết quả detection hiện tại"""
    with detections_lock:
        return jsonify({
            "person_count": person_count,
            "detections": list(detections),
            "yolo_enabled": yolo_enabled,
            "detect_fps": detect_fps
        })


# ===================== VIRTUAL FENCE API =====================

@app.route('/api/fence/set', methods=['POST'])
def api_fence_set():
    """Lưu polygon vùng cấm (tọa độ chuẩn hóa 0.0-1.0)"""
    global fence_polygon
    data = request.get_json()
    if not data or 'points' not in data:
        return jsonify({"error": "Missing 'points' in body"}), 400

    points = data['points']
    # Validate: cần ít nhất 3 điểm
    if len(points) < 3:
        return jsonify({"error": "Need at least 3 points for polygon"}), 400

    with fence_lock:
        fence_polygon = [[float(p[0]), float(p[1])] for p in points]

    print(f"[FENCE] Polygon set: {len(fence_polygon)} points")
    return jsonify({"status": "ok", "points": len(fence_polygon)})


@app.route('/api/fence/get')
def api_fence_get():
    """Lấy polygon hiện tại"""
    with fence_lock:
        return jsonify({"points": list(fence_polygon)})


@app.route('/api/fence/clear')
def api_fence_clear():
    """Xóa polygon"""
    global fence_polygon
    with fence_lock:
        fence_polygon = []
    print("[FENCE] Polygon cleared")
    return jsonify({"status": "cleared"})


# ===================== ALERT API =====================

@app.route('/api/alert/toggle')
def api_alert_toggle():
    """Bật/tắt tự động cảnh báo khi xâm nhập"""
    global auto_alert_enabled
    auto_alert_enabled = not auto_alert_enabled
    state = "ON" if auto_alert_enabled else "OFF"
    print(f"[ALERT] Auto alert: {state}")
    return jsonify({"auto_alert_enabled": auto_alert_enabled})


@app.route('/api/alert/test')
def api_alert_test():
    """Test cảnh báo (bật buzzer tạm thời)"""
    threading.Thread(target=auto_buzzer_alert, daemon=True).start()
    return jsonify({"status": "testing"})


# ===================== INTRUSION LOG API =====================

@app.route('/api/logs')
def api_logs():
    """Lấy danh sách intrusion log"""
    with log_lock:
        # Trả về 50 entries gần nhất, mới nhất trước
        recent = list(reversed(intrusion_log[-50:]))
    return jsonify({"logs": recent, "total": len(intrusion_log)})


@app.route('/api/logs/clear')
def api_logs_clear():
    """Xóa toàn bộ log"""
    global intrusion_log
    with log_lock:
        intrusion_log = []
    # Xóa file log
    try:
        log_path = os.path.join(config.LOG_DIR, "intrusion_log.json")
        if os.path.exists(log_path):
            os.remove(log_path)
    except:
        pass
    return jsonify({"status": "cleared"})


@app.route('/api/logs/image/<filename>')
def api_log_image(filename):
    """Xem ảnh intrusion log"""
    # Bảo mật: chỉ cho phép tên file an toàn
    import re
    if not re.match(r'^intrusion_\d{8}_\d{6}(_\d+)?\.jpg$', filename):
        return jsonify({"error": "Invalid filename"}), 400
    image_path = os.path.join(config.LOG_DIR, filename)
    if not os.path.exists(image_path):
        return jsonify({"error": "Image not found"}), 404
    with open(image_path, 'rb') as f:
        image_data = f.read()
    return Response(image_data, mimetype='image/jpeg')


@app.route('/api/esp32/buzzer/<action>')
def api_buzzer(action):
    try:
        if action == "on":
            r = requests.get(config.ESP32_BUZZER_ON_URL, timeout=2)
        elif action == "off":
            r = requests.get(config.ESP32_BUZZER_OFF_URL, timeout=2)
        else:
            return jsonify({"error": "Invalid action. Use 'on' or 'off'"}), 400
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/snapshot')
def api_snapshot():
    with frame_lock:
        if yolo_enabled and detected_frame is not None:
            frame = detected_frame.copy()
        elif current_frame is not None:
            frame = current_frame.copy()
        else:
            frame = None

    if frame is None:
        return jsonify({"error": "No frame available"}), 503

    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if ret:
        return Response(jpeg.tobytes(), mimetype='image/jpeg',
                        headers={"Content-Disposition": "inline; filename=snapshot.jpg"})
    return jsonify({"error": "Encode failed"}), 500


# ===================== MAIN =====================
if __name__ == '__main__':
    os.makedirs(config.LOG_DIR, exist_ok=True)

    # Tải intrusion log từ file
    load_log_from_file()

    # Thread 1: Đọc stream từ ESP32-CAM
    stream_thread = threading.Thread(target=read_esp32_stream, daemon=True)
    stream_thread.start()

    # Thread 2: YOLO detection loop
    detect_thread = threading.Thread(target=yolo_detection_loop, daemon=True)
    detect_thread.start()

    print(f"\n{'='*55}")
    print(f"   SENTINEL EYE - Python Server (YOLO Enabled)")
    print(f"{'='*55}")
    print(f"  Server:     http://localhost:{config.SERVER_PORT}")
    print(f"  ESP32:      {config.ESP32_IP}")
    print(f"  YOLO Model: {config.YOLO_MODEL}")
    print(f"  Confidence: {config.YOLO_CONFIDENCE}")
    print(f"  Detect Every: {config.YOLO_DETECT_INTERVAL} frame(s)")
    print(f"{'='*55}")
    print(f"  Endpoints:")
    print(f"    /                      - Web Dashboard")
    print(f"    /video_feed            - MJPEG stream (with detection)")
    print(f"    /api/status            - System status")
    print(f"    /api/detections        - Current YOLO detections")
    print(f"    /api/yolo/toggle       - Toggle YOLO on/off")
    print(f"    /api/yolo/confidence/X - Set confidence (0.0-1.0)")
    print(f"    /api/snapshot          - Capture frame")
    print(f"    /api/fence/set         - Set fence polygon (POST)")
    print(f"    /api/fence/get         - Get fence polygon")
    print(f"    /api/fence/clear       - Clear fence polygon")
    print(f"    /api/esp32/buzzer/on   - Buzzer ON")
    print(f"    /api/esp32/buzzer/off  - Buzzer OFF")
    print(f"    /api/alert/toggle      - Toggle auto alert")
    print(f"    /api/alert/test        - Test buzzer alert")
    print(f"    /api/logs              - Intrusion log")
    print(f"    /api/logs/clear        - Clear logs")
    print(f"    /api/logs/image/<file> - View log image")
    print(f"{'='*55}\n")

    app.run(host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.DEBUG_MODE,
            threaded=True,
            use_reloader=False)
