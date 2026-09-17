# 🧠 SENTINEL EYE — Hướng Dẫn Fine-Tuning YOLOv8

## Tại sao cần Fine-Tuning?

Model **YOLOv8n** mặc định được train trên **COCO dataset** (330K ảnh, 80 class) — đây là dataset chung chung, chụp bằng camera chuyên nghiệp, độ phân giải cao, ánh sáng tốt.

Camera **ESP32-CAM** của bạn có đặc điểm riêng:
- Độ phân giải thấp (VGA 640×480 hoặc QVGA 320×240)
- Góc camera cố định
- Ánh sáng môi trường cụ thể (trong nhà, ban đêm...)
- Chất lượng ảnh bị nhiễu, nén JPEG mạnh

**Fine-tuning** giúp model "học" lại đặc điểm riêng của camera bạn → nhận diện người chính xác hơn trong điều kiện thực tế.

---

## Tổng Quan Quy Trình

```
[1] Thu thập ảnh    →  [2] Gán nhãn     →  [3] Tổ chức dataset
    (collect_images.py)    (Roboflow.com)      (tự động từ Roboflow)
    
→  [4] Fine-tune    →  [5] Đánh giá    →  [6] Triển khai
   (train.py)           (evaluate.py)       (đổi config.py)
```

**Thời gian ước tính**: 2-3 giờ (bao gồm gán nhãn)

---

## Cấu Trúc Thư Mục

```
fine_tuning/
├── collect_images.py     ← Script chụp ảnh từ ESP32
├── train.py              ← Script train model
├── evaluate.py           ← Script đánh giá so sánh
├── raw_images/           ← Ảnh thô chụp từ ESP32 (sau khi chạy collect)
├── dataset/              ← Dataset đã gán nhãn
│   ├── data.yaml         ← File cấu hình (đã tạo sẵn)
│   ├── train/
│   │   ├── images/       ← 80% ảnh training
│   │   └── labels/       ← File nhãn .txt tương ứng
│   └── val/
│       ├── images/       ← 20% ảnh validation
│       └── labels/       ← File nhãn .txt tương ứng
└── HUONG_DAN_FINE_TUNING.md  ← File này
```

---

## Bước 1: Thu Thập Ảnh Từ ESP32-CAM

### 1.1 Chuẩn bị

- ESP32-CAM phải **đang bật** và kết nối WiFi
- Máy tính **cùng mạng WiFi** với ESP32
- Kiểm tra IP ESP32 trong `server/config.py`

### 1.2 Chạy script thu thập

```bash
cd HCL/fine_tuning
python collect_images.py
```

Script sẽ tự động chụp **80 ảnh**, mỗi 2 giây 1 ảnh (~3 phút).

### 1.3 Trong lúc chụp, bạn cần:

| Hành động | Số ảnh (~) | Lý do |
|---|---|---|
| **Đi lại** trước camera (gần/xa) | 25 | Model học người ở nhiều khoảng cách |
| **Đứng yên** ở nhiều vị trí | 15 | Model học người đứng im |
| **Quay lưng / nghiêng** | 10 | Model học nhiều góc nhìn |
| **2 người** cùng lúc | 10 | Model học phát hiện nhiều người |
| **Không ai** trước camera | 15 | Model học phân biệt nền trống |
| Ánh sáng yếu / đèn tắt | 5 | Nếu hệ thống chạy ban đêm |

> 💡 **Mẹo**: Đa dạng > Số lượng. 80 ảnh đa dạng tốt hơn 300 ảnh giống nhau.

### 1.4 Kiểm tra ảnh

Sau khi chụp xong, mở thư mục `fine_tuning/raw_images/` và:
- **Xóa** ảnh mờ, đen, hoặc lỗi
- **Giữ lại** tối thiểu 50 ảnh tốt
- Đảm bảo có cả ảnh **có người** và **không có người**

---

## Bước 2: Gán Nhãn Trên Roboflow (Miễn Phí)

### 2.1 Tạo tài khoản

1. Truy cập **https://roboflow.com** → Đăng ký tài khoản miễn phí
2. Nhấn **"Create New Project"**
3. Cấu hình:
   - **Project Name**: `Sentinel Eye`
   - **Project Type**: `Object Detection`
   - **Annotation Group**: `person`
   - **License**: để mặc định

### 2.2 Upload ảnh

1. Nhấn **"Upload Data"**
2. Kéo thả toàn bộ ảnh từ `fine_tuning/raw_images/` vào
3. Chờ upload xong
4. Nhấn **"Save and Continue"**

### 2.3 Gán nhãn (Annotate)

Đây là bước **tốn thời gian nhất** (~1-1.5 giờ cho 80 ảnh):

1. Nhấn **"Annotate"** → chọn ảnh đầu tiên
2. Chọn công cụ **Bounding Box** (hộp chữ nhật)
3. Vẽ hộp bao quanh **mỗi người** trong ảnh:
   - Kéo chuột từ góc trái trên → góc phải dưới
   - Bao trùm toàn bộ cơ thể người (từ đầu đến chân)
   - Gán class: **`person`**
4. Nếu ảnh **không có người** → bỏ qua (không vẽ gì), nhấn **Save** luôn
5. Lặp lại cho tất cả ảnh

> ⚠️ **Lưu ý quan trọng khi gán nhãn:**
> - Bounding box phải **bao sát** người, không quá to cũng không quá nhỏ
> - Nếu người bị che khuất >50%, có thể bỏ qua
> - Ảnh không có người **vẫn giữ** (negative sample), chỉ không vẽ box

### 2.4 Tạo Dataset Version

1. Sau khi gán nhãn xong → nhấn **"Generate"**
2. **Train/Valid Split**: 80% / 20% (để mặc định)
3. **Preprocessing**:
   - Auto-Orient: ✅
   - Resize: **640×640** (Stretch)
4. **Augmentation** (tăng cường dữ liệu — RẤT QUAN TRỌNG khi ít ảnh):
   - **Flip**: Horizontal ✅
   - **Rotation**: -15° đến +15° ✅
   - **Brightness**: -15% đến +15% ✅ 
   - **Blur**: Up to 1px ✅
   - **Noise**: Up to 2% ✅
5. Nhấn **"Generate"** → chờ xử lý

> 💡 **Augmentation** tự động tạo thêm ảnh biến thể (lật, xoay, đổi sáng...) từ ảnh gốc. 80 ảnh gốc có thể trở thành 200-400 ảnh training nhờ augmentation!

### 2.5 Export Dataset

1. Nhấn **"Export Dataset"**
2. Format: **YOLOv8**
3. Chọn **"download zip to computer"**
4. Tải file `.zip` về máy

---

## Bước 3: Tổ Chức Dataset

### 3.1 Giải nén file tải về

Giải nén file `.zip` từ Roboflow. Bên trong sẽ có:

```
(file giải nén)/
├── data.yaml
├── train/
│   ├── images/
│   └── labels/
├── valid/          ← Roboflow đặt tên "valid" thay vì "val"
│   ├── images/
│   └── labels/
└── test/           ← Có thể có hoặc không
```

### 3.2 Copy vào thư mục dự án

Copy nội dung vào `fine_tuning/dataset/`:

```bash
# Windows - mở File Explorer:
# 1. Copy NỘI DUNG thư mục train/ → fine_tuning/dataset/train/
# 2. Copy NỘI DUNG thư mục valid/ → fine_tuning/dataset/val/
#    (Lưu ý: Roboflow đặt tên "valid", project dùng "val")
```

**Hoặc** đơn giản hơn: **ghi đè** file `data.yaml` trong `fine_tuning/dataset/` bằng file `data.yaml` từ Roboflow, rồi sửa đường dẫn:

```yaml
# Sửa data.yaml cho đúng đường dẫn
train: ./train/images
val: ./val/images    # Đổi "valid" thành "val" nếu cần

nc: 1
names: ['person']
```

### 3.3 Kiểm tra

Đảm bảo cấu trúc đúng:
```
fine_tuning/dataset/
├── data.yaml
├── train/
│   ├── images/     ← Có ảnh .jpg
│   └── labels/     ← Có file .txt tương ứng
└── val/
    ├── images/     ← Có ảnh .jpg
    └── labels/     ← Có file .txt tương ứng
```

Mỗi file `.txt` trong labels chứa nhãn YOLO format:
```
0 0.45 0.52 0.25 0.80
```
(class_id center_x center_y width height — tất cả chuẩn hóa 0.0-1.0)

---

## Bước 4: Fine-Tune Model

### 4.1 Cài đặt thư viện (nếu chưa có)

```bash
pip install ultralytics
```

### 4.2 Chạy training

```bash
cd HCL/fine_tuning
python train.py
```

### 4.3 Quá trình training

Script sẽ:
1. Load model `yolov8n.pt` (pre-trained)
2. **Freeze 10 lớp đầu** — chỉ train lại lớp cuối (transfer learning)
3. Train 50 epochs trên dataset của bạn
4. Tự động dừng sớm nếu 15 epoch không cải thiện
5. Copy model tốt nhất (`best.pt`) thành `server/sentinel_eye.pt`

### 4.4 Thời gian ước tính

| Phần cứng | Thời gian |
|---|---|
| GPU NVIDIA (GTX 1060+) | 10-20 phút |
| CPU hiện đại (i5/i7) | 1-3 giờ |
| CPU yếu | 3-5 giờ |

> 💡 **Nếu có GPU NVIDIA**: Cài `pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu118` để tăng tốc.

### 4.5 Kết quả training

Sau khi train xong, kiểm tra thư mục:
```
runs/detect/sentinel_eye_finetune/
├── weights/
│   ├── best.pt         ← Model tốt nhất (đã copy vào server/)
│   └── last.pt         ← Model epoch cuối cùng
├── results.png         ← Biểu đồ loss/metrics
├── confusion_matrix.png
├── val_batch0_pred.jpg ← Ảnh dự đoán trên validation set
└── ...
```

---

## Bước 5: Đánh Giá Model

### 5.1 So sánh model gốc vs fine-tuned

```bash
cd HCL/fine_tuning
python evaluate.py
```

Script sẽ hiển thị bảng so sánh:
```
  Metric          Gốc   Fine-tuned  Thay đổi
  -----------------------------------------------
  mAP50          0.7500       0.9200   +0.1700 ↑
  mAP50-95       0.4500       0.6800   +0.2300 ↑
  Precision      0.8000       0.9100   +0.1100 ↑
  Recall         0.7200       0.8800   +0.1600 ↑
```

### 5.2 Các metric quan trọng

| Metric | Ý nghĩa | Tốt khi |
|---|---|---|
| **mAP50** | Độ chính xác trung bình (IoU=0.5) | > 0.80 |
| **Precision** | Tỉ lệ dự đoán đúng / tổng dự đoán | > 0.85 |
| **Recall** | Tỉ lệ phát hiện được / tổng thực tế | > 0.80 |

---

## Bước 6: Triển Khai Model Mới

### 6.1 Cập nhật config

Mở `server/config.py`, đổi:

```python
# Trước:
YOLO_MODEL = "yolov8n.pt"

# Sau:
YOLO_MODEL = "sentinel_eye.pt"
```

### 6.2 Restart server

```bash
cd HCL/server
python app.py
```

Server sẽ hiện:
```
[YOLO] Đang tải model sentinel_eye.pt...
[YOLO] Model loaded thành công!
```

### 6.3 Test

Mở Dashboard → kiểm tra detection có tốt hơn không.

Nếu muốn **quay lại model cũ**, chỉ cần đổi `YOLO_MODEL = "yolov8n.pt"` trong config.

---

## Mẹo & Khắc Phục Sự Cố

### ❌ Model fine-tuned tệ hơn model gốc

| Nguyên nhân | Giải pháp |
|---|---|
| Quá ít ảnh (< 30) | Chụp thêm ảnh, dùng augmentation mạnh hơn |
| Gán nhãn sai | Kiểm tra lại bounding box trên Roboflow |
| Overfitting | Giảm epochs xuống 30, tăng patience |
| Ảnh không đa dạng | Chụp nhiều góc, khoảng cách, ánh sáng khác nhau |

### ❌ Lỗi CUDA out of memory

```python
# Trong train.py, giảm batch size:
BATCH_SIZE = 4  # hoặc 2
```

### ❌ Training quá chậm trên CPU

```python
# Trong train.py, giảm:
EPOCHS = 30
IMG_SIZE = 320  # nhỏ hơn = nhanh hơn
```

### 💡 Muốn model chính xác hơn nữa?

1. Thu thập thêm ảnh (100-200 ảnh)
2. Sử dụng model lớn hơn: `yolov8s.pt` (small) thay vì `yolov8n.pt` (nano)
3. Tăng epochs lên 100
4. Bỏ `freeze=10` để train toàn bộ model (cần nhiều data hơn)

---

## Tóm Tắt Nhanh

```bash
# 1. Chụp ảnh
cd fine_tuning
python collect_images.py

# 2. Gán nhãn trên roboflow.com → export YOLOv8 → giải nén vào dataset/

# 3. Train
python train.py

# 4. Đánh giá
python evaluate.py

# 5. Triển khai: sửa server/config.py → YOLO_MODEL = "sentinel_eye.pt"
# 6. Restart: python app.py
```

---

> 🧠 **Fine-tuning = Dạy model cũ "nhìn" qua mắt camera của bạn.** Chỉ cần 50-80 ảnh đã gán nhãn là có thể cải thiện đáng kể độ chính xác!
