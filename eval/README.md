# Hồ sơ đánh giá · CP3

## 1. Dataset → xử lý

Đọc CSV địa điểm, giá và tuyến theo vùng Hà Giang hoặc Đà Nẵng. Vé phải khớp mã điểm, mã giá và đơn vị. Lịch mẫu dùng chi phí tại điểm đến cho chỗ ở, thuê xe và vé. Ngày mưa lấy từ kịch bản nhập, không dùng dự báo live. Xem [data card](../data/DATA_CARD.md).

## 2. Bộ câu thử dựng ra sao

- [Benchmark](benchmark.csv) có 22 câu gồm 8 thường, 12 khó và 2 từ chối. Có 13 câu dựa trên dữ kiện trong CSV và 9 câu tự viết. Kịch bản mưa là dữ liệu giả lập.
- Độ phủ: điểm đến và số ngày; ngân sách bình thường, sát ngưỡng hoặc thiếu; thời điểm thiếu hoặc đủ; một ngày mưa, cảnh báo hoặc chưa biết; yêu cầu trong phạm vi hoặc vượt quyền.
- B03, B04 và B10 kiểm dữ liệu nguồn. B07, B12 và B13 kiểm cách hỏi lại. B14 và B15 kiểm phạm vi quyền. B08, B09 và B11 kiểm ngân sách và ngày có cảnh báo.
- B16–B22 kiểm trần ngân sách, thiếu ứng viên, giữ hoạt động trong nhà đã có, mưa nguy hiểm, nhiều ngày mưa, đổi điểm vé cao và ngân sách cả nhóm.

## 3. Metric và cách chấm

| Metric | Cách chấm | Ngưỡng |
|---|---|---|
| `ngan_sach_va_nguon` | Đối chiếu tổng, mã giá, vùng và đơn vị với CSV | 100% câu có lịch |
| `xu_ly_ngay_mua` | Đối chiếu ngày bị đổi hoặc bỏ trống, căn cứ và nhãn thời tiết | 100% câu có ngày mưa hợp lệ |
| `dung_hanh_vi_theo_cau` | Chấm tay theo `pass_criterion` | Ít nhất 80% toàn bộ, 100% câu từ chối |

**Chuẩn đạt:** “Đạt khi ít nhất 80% toàn bộ câu qua, 100% câu trả lịch đạt kiểm tra ngân sách và nguồn, 100% câu có ngày mưa hợp lệ xử lý đúng, và 100% câu từ chối đạt.”

Nhóm chưa chấm độc lập. Dùng B03, B07, B09, B10 và B14 để chấm chéo 5 output. Mỗi người dùng cột `pass_criterion` ghi 1 hoặc 0 rồi so số ca khớp (yêu cầu ít nhất 4/5).

## 4. Lệnh

Bộ câu thử và chuẩn đạt ở đây đo luồng CLI. Xem [báo cáo triển khai Streamlit](../REPORT.md).

```bash
python3 run.py check
export MODEL_PROVIDER=llamacpp MODEL_NAME=qwen3-0.6b-f16
python3 run.py
python3 run.py eval --try
```

Đầu vào mẫu cho lệnh thứ hai: `Đà Nẵng 3 ngày, ngân sách 3 triệu mỗi người, tháng 10, mưa ngày 2.`

Khởi động ứng dụng phục vụ model như trong [hướng dẫn kết nối](../docs/connect-model.md). Lấy 5 output theo mã ca ở mục 3 từ lượt chạy thật để chấm chéo.

Lệnh `python3 run.py eval` tạo lượt đánh giá mới. Nhóm duyệt và điền cột `pass` cho lượt cần chốt, sau đó chạy `python3 run.py score eval/run-1.csv`.

## 5. Đã chạy gì

| Lượt | Run ID | Model | Kết quả |
|---|---|---|---|
| 1 | `run-1@20261127-222340` | `qwen3-0.6b-f16` qua llama.cpp | 22/22 đạt (100%) theo `score`. Có 5 câu gọi model và 0 lỗi kỹ thuật. |

[CSV gốc](run-1.csv) · [Trace](../traces/run-1.jsonl) · [Đối chiếu từng câu](report.md) · [Demo web 30 giây](../slides/demo-cp3-ui.mp4)

Chạy thử mô phỏng 10 phiên, 3 phiên gọi model và 0 lỗi kỹ thuật. Bảng giá tham chiếu áp lên token đo từ Qwen, còn chi phí trên mỗi tác vụ thành công cần kết quả chấm. [Tóm tắt mô phỏng](../cost/cost-estimate.md#kiểm-tra-khung-cp3)

## 6. Lỗi chính

Các ca B10 và B17 giữ trống ngày mưa vì thiếu phương án có đủ dữ liệu hoặc vừa ngân sách. CLI nhận thời tiết theo kịch bản và benchmark hiện chỉ kiểm quyết định cho một ngày mưa.
