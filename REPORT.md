# Đi Vừa Túi · Báo cáo triển khai

Bản Streamlit lập lịch Hà Giang và Đà Nẵng từ CSV chỉ đọc, nhận ngân sách mỗi người hoặc cả nhóm và trả kế hoạch JSON. Python chọn địa điểm, lịch và chỗ ở, rồi kiểm dự toán theo cận trên của các khoản có dữ liệu. Bedrock chỉ trình bày phần đã tính. Hồ sơ CP2, benchmark và chuẩn đạt giữ riêng cho luồng CLI.

## Tệp và lệnh

| Phần | Tệp |
|---|---|
| Đọc và kiểm dữ liệu | `data_adapter.py`, `data_loader.py`, `validate_data.py`, [data_report.md](data_report.md) |
| Lập lịch, giá và thời tiết | `config.py`, `budget.py`, `planner.py`, `lodging.py`, `weather_service.py` |
| Hiển thị | `app.py`, `output.py`, `llm.py`, `prompt.md` |
| Kiểm thử và gói chạy | `tests/test_product.py`, `run.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`, [DEPLOY.md](DEPLOY.md) |

```bash
python -m pip install -r requirements.txt
python run.py check
python -m pytest -q tests
python -m streamlit run app.py
```

Ba CSV gốc được giữ nguyên. `run.py check` chạy trình kiểm tra dữ liệu chuẩn hóa, pytest và kiểm tra hồ sơ đánh giá.

## Giả định và phạm vi chi phí

- [config.py](config.py) ghi mặc định thời lượng theo nhóm 1–2 giờ, chuyến 1–5 ngày, giới hạn 6 giờ di chuyển/ngày và tốc độ quy đổi 20 km/h cho đoạn chỉ có đường chim bay. Mỗi phương án như vậy mang cờ ước tính.
- Giá chung từ hai cận dùng trung điểm, còn trần dùng cận trên. Với lưu trú một cận, giữ nguyên con số nguồn cho cả hai cận và giới hạn độ tin cậy ở mức vừa. Mặc định 2 người/phòng khi cần, một giường tính một người. Hotel/guesthouse thiếu đơn vị tạm tính theo phòng. Homestay thiếu đơn vị được xếp thấp và đưa ra khỏi phép tính giá nhóm.
- Phân bổ ngân sách theo phong cách nằm trong cấu hình. Bản thử dùng một xe/người, ba bữa/ngày nếu bảng giá có đơn vị bữa phù hợp, không tính tiền đi đến vùng, xăng và tiền cọc. Đà Nẵng thiếu giá ăn theo bữa áp dụng được, giao diện ghi tính riêng. Chi phí hiển thị là giá tham khảo, chưa xác minh còn chỗ, thuế hoặc giá hiện hành.
- Ngưỡng mưa là 60%, cửa sổ dự báo 16 ngày. Khi thiếu `weather.py`, kế hoạch ghi chưa có dự báo. Dữ liệu cache hoặc khí hậu giữ nguyên lịch và dùng nhãn riêng.

## Kiểm tra và việc còn lại

Đã chạy 16 kiểm thử local, gồm mock dự báo, cache, S3 lỗi, Bedrock và form Streamlit. Cả cấu hình có bảng lưu trú riêng và cấu hình chỉ dùng CSV đã theo dõi trong Git đều qua `run.py check`. Chưa chạy model hoặc dự báo thật. Yêu cầu chạy build Docker đã được người dùng từ chối, nên image chưa được kiểm chứng.

Các bảng lưu trú chi tiết hiện ở workspace local. Bản clone dùng bảng dự phòng nếu chưa có bộ lưu trú riêng. Để dùng đủ dữ liệu, đặt bộ CSV lưu trú lên S3 cùng prefix hoặc cung cấp ở thư mục `data/`. Bổ sung `weather.py` theo [hợp đồng tích hợp](DEPLOY.md). Nếu dùng Bedrock, cấu hình IAM và model ở môi trường triển khai.

Hồ sơ CP2 còn cần hai người chấm độc lập 5 đầu ra và ghi mức khớp thật trong [hồ sơ đánh giá](eval/README.md). Kết quả kiểm thử kỹ thuật không thay thế chấm chéo.
