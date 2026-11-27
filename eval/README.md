# Hồ sơ đánh giá · CP2

## 1. Dataset → xử lý

Đọc CSV địa điểm, giá và tuyến theo vùng Hà Giang hoặc Đà Nẵng. Vé phải khớp mã điểm, mã giá và đơn vị. Lịch mẫu dùng chi phí tại điểm đến cho chỗ ở, thuê xe và vé. Ngày mưa lấy từ kịch bản nhập, không dùng dự báo live. Xem [data card](../data/DATA_CARD.md).

## 2. Bộ câu thử dựng ra sao

- [Benchmark](benchmark.csv) có 15 câu: 6 thường, 7 khó, 2 từ chối (cả hai thử yêu cầu vượt quyền). 8/15 câu dựng từ dữ kiện trong CSV, 7 câu tự viết. Câu có kịch bản mưa ghi rõ giả lập.
- Độ phủ: điểm đến và số ngày; ngân sách bình thường, sát ngưỡng hoặc thiếu; thời điểm thiếu hoặc đủ; một ngày mưa, cảnh báo hoặc chưa biết; yêu cầu trong phạm vi hoặc vượt quyền.
- B03, B04 và B10 kiểm dữ liệu nguồn. B07, B12 và B13 kiểm cách hỏi lại. B14 và B15 kiểm phạm vi quyền. B08, B09 và B11 kiểm ngân sách và ngày có cảnh báo.

## 3. Metric và cách chấm

| Metric | Cách chấm | Ngưỡng |
|---|---|---|
| `ngan_sach_va_nguon` | Đối chiếu tổng, mã giá, vùng và đơn vị với CSV | 100% câu có lịch |
| `xu_ly_ngay_mua` | Đối chiếu ngày bị đổi hoặc bỏ trống, căn cứ và nhãn thời tiết | 100% câu có ngày mưa hợp lệ |
| `dung_hanh_vi_theo_cau` | Chấm tay theo `pass_criterion` | Ít nhất 80% toàn bộ, 100% câu từ chối |

**Chuẩn đạt:** “Đạt khi ít nhất 80% toàn bộ câu qua, 100% câu trả lịch đạt kiểm tra ngân sách và nguồn, 100% câu có ngày mưa hợp lệ xử lý đúng, và 100% câu từ chối đạt.”

Chưa có kết quả hai người chấm độc lập. Dùng B03, B07, B09, B10 và B14 để chấm chéo 5 output. Mỗi người dùng cột `pass_criterion` ghi 1 hoặc 0 rồi so số ca khớp (yêu cầu ít nhất 4/5). CP2 chưa có lượt đánh giá chính thức với model thật.

## 4. Lệnh

Bộ câu thử và chuẩn đạt ở đây đo luồng CLI CP2. Bản Streamlit dùng pytest riêng; xem [báo cáo](../REPORT.md).

```bash
python3 run.py check
MODEL_PROVIDER=fake python3 run.py
MODEL_PROVIDER=fake python3 run.py eval --try
```

Đầu vào mẫu cho lệnh thứ hai: `Đà Nẵng 3 ngày, ngân sách 3 triệu mỗi người, tháng 10, mưa ngày 2.`

Để lấy 5 output chấm chéo, chạy `MODEL_PROVIDER=fake python3 run.py eval --try 14` ở bản sao repo dùng cho kiểm tra, rồi lấy các mã trên trong `eval/run-try.csv`.

Sau khi nối model thật, chạy `python3 run.py eval`, chấm cột `pass`, rồi chạy `python3 run.py score eval/run-1.csv`.

## 5. Đã chạy gì

Đã chạy đủ 15 câu bằng model giả trong bản sao repo. Bộ chạy ghi `run-mock.csv`, chưa tính vào lượt đánh giá. Kiểm tra smoke xác nhận tổng và ngân sách, khoanh vùng địa điểm và chặn mã ngoài danh sách. Lượt 1 và lượt 2 sẽ ghi bảng kết quả khi có run ID của model thật.

## 6. Lỗi chính

Chưa phân tích lỗi từ lượt chạy chính thức. Rủi ro đã biết là thiếu tuyến/giá ở một số địa điểm, và chưa có ứng viên đổi ngày mưa đạt điều kiện tại Hà Giang.
