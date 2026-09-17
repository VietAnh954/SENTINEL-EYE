# ============================================================
# SENTINEL EYE - Script Thu Thập Ảnh Từ ESP32-CAM
# Chạy: python collect_images.py
# Mục đích: Chụp ảnh tự động từ ESP32-CAM để tạo dataset fine-tuning
# ============================================================

import requests
import os
import time
import sys
from datetime import datetime

# ===================== CẤU HÌNH =====================
# Tự động lấy IP từ config.py của server
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'server'))
try:
    import config
    ESP32_IP = config.ESP32_IP
except:
    ESP32_IP = "192.168.16.75"  # Fallback IP

ESP32_CAPTURE_URL = f"http://{ESP32_IP}/capture"

# Thư mục lưu ảnh thu thập
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_images")

# Số ảnh muốn chụp
TOTAL_IMAGES = 80

# Khoảng cách giữa mỗi lần chụp (giây)
CAPTURE_INTERVAL = 2


# ===================== MAIN =====================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Đếm ảnh đã có
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.jpg')]
    start_index = len(existing)

    print("=" * 55)
    print("  SENTINEL EYE - Thu Thập Ảnh Fine-Tuning")
    print("=" * 55)
    print(f"  ESP32-CAM:     {ESP32_IP}")
    print(f"  Capture URL:   {ESP32_CAPTURE_URL}")
    print(f"  Thư mục lưu:   {OUTPUT_DIR}")
    print(f"  Ảnh đã có:     {start_index}")
    print(f"  Mục tiêu:      {TOTAL_IMAGES} ảnh")
    print(f"  Khoảng cách:   {CAPTURE_INTERVAL}s / ảnh")
    print(f"  Thời gian ước: ~{(TOTAL_IMAGES - start_index) * CAPTURE_INTERVAL}s")
    print("=" * 55)
    print()
    print("HƯỚNG DẪN: Di chuyển trước camera ở nhiều vị trí khác nhau!")
    print("  - Đi lại gần/xa camera")
    print("  - Đứng yên, quay lưng, nghiêng người")
    print("  - Thay đổi ánh sáng nếu có thể")
    print("  - Có lúc KHÔNG có người trước camera (ảnh nền)")
    print()
    input("Nhấn ENTER để bắt đầu chụp...")
    print()

    success_count = 0
    fail_count = 0

    for i in range(start_index, TOTAL_IMAGES):
        try:
            response = requests.get(ESP32_CAPTURE_URL, timeout=5)
            if response.status_code == 200 and len(response.content) > 1000:
                filename = f"img_{i+1:04d}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                success_count += 1
                print(f"  ✅ [{i+1}/{TOTAL_IMAGES}] {filename} ({len(response.content)//1024}KB)")
            else:
                fail_count += 1
                print(f"  ❌ [{i+1}/{TOTAL_IMAGES}] Ảnh lỗi (size={len(response.content)})")
        except requests.exceptions.ConnectionError:
            fail_count += 1
            print(f"  ❌ [{i+1}/{TOTAL_IMAGES}] Không kết nối được ESP32!")
        except requests.exceptions.Timeout:
            fail_count += 1
            print(f"  ❌ [{i+1}/{TOTAL_IMAGES}] Timeout!")
        except Exception as e:
            fail_count += 1
            print(f"  ❌ [{i+1}/{TOTAL_IMAGES}] Lỗi: {e}")

        # Chờ trước ảnh tiếp
        if i < TOTAL_IMAGES - 1:
            time.sleep(CAPTURE_INTERVAL)

    print()
    print("=" * 55)
    print(f"  HOÀN TẤT!")
    print(f"  Thành công: {success_count} ảnh")
    print(f"  Thất bại:   {fail_count}")
    print(f"  Thư mục:    {OUTPUT_DIR}")
    print("=" * 55)
    print()
    print("BƯỚC TIẾP THEO:")
    print("  1. Lên https://roboflow.com → tạo project → upload ảnh")
    print("  2. Gán nhãn (vẽ bounding box quanh người)")
    print("  3. Export format 'YOLOv8' → tải về")
    print("  4. Giải nén vào thư mục fine_tuning/dataset/")
    print("  5. Chạy: python train.py")


if __name__ == "__main__":
    main()
