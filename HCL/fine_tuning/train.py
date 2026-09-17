# ============================================================
# SENTINEL EYE - Script Fine-Tuning YOLOv8
# Chạy: python train.py
# Yêu cầu: đã cài ultralytics (pip install ultralytics)
# ============================================================

from ultralytics import YOLO
import os
import shutil

# ===================== CẤU HÌNH =====================
# Model gốc (pre-trained trên COCO) - dùng làm điểm xuất phát
BASE_MODEL = "yolov8n.pt"

# File cấu hình dataset
DATA_YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset", "data.yaml")

# Tham số training
EPOCHS = 50           # Số vòng train (50 là đủ cho fine-tuning)
IMG_SIZE = 640        # Kích thước ảnh (giữ 640 cho VGA)
BATCH_SIZE = 8        # Giảm xuống 4 nếu thiếu RAM/GPU
PATIENCE = 15         # Dừng sớm nếu 15 epoch không cải thiện

# Tên experiment
PROJECT_NAME = "sentinel_eye_finetune"


# ===================== MAIN =====================
def main():
    print("=" * 55)
    print("  SENTINEL EYE - Fine-Tuning YOLOv8")
    print("=" * 55)

    # Kiểm tra dataset
    if not os.path.exists(DATA_YAML):
        print(f"\n❌ Không tìm thấy file: {DATA_YAML}")
        print("\nHƯỚNG DẪN:")
        print("  1. Gán nhãn ảnh trên Roboflow.com")
        print("  2. Export format 'YOLOv8'")
        print("  3. Giải nén vào thư mục: fine_tuning/dataset/")
        print("  4. Đảm bảo có file data.yaml bên trong")
        return

    print(f"\n  Base Model:  {BASE_MODEL}")
    print(f"  Dataset:     {DATA_YAML}")
    print(f"  Epochs:      {EPOCHS}")
    print(f"  Image Size:  {IMG_SIZE}")
    print(f"  Batch Size:  {BATCH_SIZE}")
    print(f"  Patience:    {PATIENCE}")
    print(f"  Project:     {PROJECT_NAME}")
    print("=" * 55)

    # Load model pre-trained
    print(f"\n[1/3] Đang tải model {BASE_MODEL}...")
    model = YOLO(BASE_MODEL)
    print("  ✅ Model loaded thành công!")

    # Fine-tune
    print(f"\n[2/3] Bắt đầu fine-tuning ({EPOCHS} epochs)...")
    print("  ⏳ Quá trình này có thể mất 15-30 phút (GPU) hoặc 2-4 giờ (CPU)...")
    print()

    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        name=PROJECT_NAME,
        patience=PATIENCE,
        pretrained=True,
        optimizer="auto",
        verbose=True,
        # Freeze 10 lớp đầu (chỉ train lớp cuối) - giúp train nhanh + ít data
        freeze=10,
    )

    # Copy model tốt nhất vào thư mục server
    print(f"\n[3/3] Xuất model...")
    best_model_path = os.path.join("runs", "detect", PROJECT_NAME, "weights", "best.pt")
    
    if os.path.exists(best_model_path):
        # Copy vào thư mục server
        server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server")
        output_name = "sentinel_eye.pt"
        output_path = os.path.join(server_dir, output_name)
        shutil.copy2(best_model_path, output_path)

        print(f"  ✅ Model đã copy vào: {output_path}")
        print()
        print("=" * 55)
        print("  FINE-TUNING HOÀN TẤT!")
        print("=" * 55)
        print()
        print("  BƯỚC TIẾP THEO:")
        print(f"  1. Mở server/config.py")
        print(f'  2. Đổi: YOLO_MODEL = "{output_name}"')
        print(f"  3. Restart server: python app.py")
        print()
        print(f"  Model mới:  {output_path}")
        print(f"  Model cũ:   server/yolov8n.pt (vẫn giữ làm backup)")
    else:
        print(f"  ❌ Không tìm thấy model: {best_model_path}")
        print("  Kiểm tra lại quá trình training.")


if __name__ == "__main__":
    main()
