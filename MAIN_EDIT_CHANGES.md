# Tài liệu Thay đổi - main_edit.py

File `main_edit.py` được tạo dựa trên `main.py` với các tối ưu chuyên gia sau:

## 1. Linh hoạt xác nhận đa khung M5
- **Thay đổi**: M5 chỉ cấm khi ngược hướng rõ ràng, cho phép NEUTRAL
- **Vị trí**: 
  - Hàm `snapshot_m5_confirmed()` (dòng ~196-227)
  - Logic `m5_allows` trong `run_once()` (dòng ~458)
- **Chi tiết**:
  - M5 chỉ block khi TẤT CẢ 3 nến đều ngược hướng
  - Cho phép NEUTRAL không cấm
  - Gates logic: `m5_allows = (side_m5 == side_m15) or (side_m5 == "NEUTRAL")`

## 2. Tăng ngưỡng điểm và ADX
- **Thay đổi**:
  - M15 threshold: 15 (trước: 9.5)
  - H1 threshold: 8 (giữ nguyên)
  - ADX H1 threshold: 28 (trước: 25)
  - Heavy hits required: 3 (giữ nguyên)
- **Vị trí**: Hàm `run_once()` (dòng ~360-365)
- **Code**:
  ```python
  th_m15 = float((cfg.get("thresholds") or {}).get("M15", 15.0))
  th_h1 = float((cfg.get("thresholds") or {}).get("H1", 8.0))
  adx_h1_threshold = int(cfg.get("adx_h1_threshold", 28))
  heavy_required = int(cfg.get("tight_mode", {}).get("heavy_required", 3))
  ```

## 3. Bộ lọc biên độ đảo chiều theo ATR
- **Thay đổi**: Chỉ vào lệnh nếu giá lệch với lệnh trước >= 0.7 * ATR
- **Vị trí**: 
  - Hàm mới `check_atr_reversal_filter()` (dòng ~172-193)
  - Áp dụng trước khi mở lệnh breakout (dòng ~529)
- **Chi tiết**:
  ```python
  def check_atr_reversal_filter(symbol, timeframe, price_now, atr_val, min_atr_mult=0.7):
      # Kiểm tra xem giá có lệch đủ so với lệnh trước không
      # Trả về True nếu |price_now - last_entry| >= 0.7 * ATR
  ```

## 4. snapshot_m5_confirmed cần 3 nến đồng pha
- **Thay đổi**: Yêu cầu 3 nến M5 đồng pha, chỉ cấm khi M5 ngược rõ
- **Vị trí**: Hàm `snapshot_m5_confirmed()` (dòng ~196-227)
- **Logic**:
  - Đếm số nến đồng pha và ngược chiều
  - Chỉ cấm khi ≥3 nến ngược chiều
  - Cho phép nếu có NEUTRAL hoặc hỗn hợp

## 5. should_send_new_entry nâng lên 0.5%
- **Thay đổi**: Ngưỡng min_entry_diff_pct từ 0.3% lên 0.5%
- **Vị trí**: Hàm `should_send_new_entry()` (dòng ~117)
- **Code**:
  ```python
  def should_send_new_entry(symbol, timeframe, direction, entry, sl, tp, 
                           min_interval_min=15, min_entry_diff_pct=0.5):
  ```

## 6. Logging các trường hợp đảo chiều liên tiếp
- **Thay đổi**: Theo dõi và log đảo chiều, bỏ qua nếu quá nhiều
- **Vị trí**: 
  - Biến global `REVERSAL_TRACKER` (dòng ~44)
  - Logic trong `should_send_new_entry()` (dòng ~124-149)
- **Chi tiết**:
  - Theo dõi số lần đảo chiều liên tiếp
  - Log cảnh báo với số thứ tự đảo chiều
  - Bỏ qua tín hiệu nếu ≥3 lần đảo chiều trong 1 giờ
  - Reset bộ đếm khi tín hiệu cùng chiều

## 7. Mọi đoạn logic khác giữ nguyên
- Async loop
- Fetch data
- Báo cáo
- Trade simulator
- Notifier
- Trailing stop
- Promote logic
- Close logic

## Sử dụng
Chạy file mới:
```bash
python main_edit.py --profile strict
```

Hoặc:
```bash
python main_edit.py --profile medium
```

File này hoàn toàn độc lập với `main.py` và có thể chạy song song hoặc thay thế.
