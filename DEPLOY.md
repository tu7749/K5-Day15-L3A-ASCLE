# Chạy và triển khai Đi Vừa Túi

## Máy local

Từ thư mục repo với Python 3.10 trở lên:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py check
python -m streamlit run app.py
```

Streamlit dùng `places.csv`, `costs.csv` và `routes.csv`. Để hiện bảng giá theo cơ sở, thêm `data/lodging.csv` đúng schema hoặc đặt cả `data/accommodations.csv` và `data/accommodation_prices.csv` bên cạnh ba tệp trên. Khi thiếu toàn bộ bảng lưu trú riêng, bản local dùng giá tham khảo dự phòng trong `costs.csv` nếu có. Hướng dẫn luồng đánh giá hackathon nằm trong [eval/README.md](eval/README.md).

Tệp `weather.py` ở gốc repo do nhóm cung cấp. Giao diện tích hợp `get_weather(latitude, longitude, target_date)`, với `target_date` là `datetime.date`. Hàm trả dict với `source` (`forecast`, `climatology`, `cache` hoặc `unavailable`), `rain_prob` từ 0 đến 1 khi có dữ liệu và tùy chọn `source_date`, `severe`. Thiếu module hoặc không lấy được dữ liệu thì ứng dụng hiển thị trạng thái tương ứng.

## EC2 với Docker

```bash
git clone https://github.com/tu7749/K5-Day15-L3A-ASCLE.git
cd K5-Day15-L3A-ASCLE
docker build -t di-vua-tui .
docker run -d --name di-vua-tui --restart unless-stopped \
  -p 80:8501 \
  -e AWS_REGION \
  -e S3_BUCKET \
  -e S3_PREFIX \
  -e BEDROCK_MODEL_ID \
  di-vua-tui
```

Đặt biến môi trường ở shell EC2 trước khi chạy lệnh. `S3_BUCKET` và `BEDROCK_MODEL_ID` là tùy chọn. `S3_PREFIX` mặc định là `data`. Đặt cả bộ CSV dưới cùng prefix. Đính IAM role vào EC2 với quyền đọc đối tượng của prefix, liệt kê prefix để phát hiện tệp tùy chọn không có và `bedrock:InvokeModel` cho model đã duyệt. Nếu container chưa lấy được credential từ IAM role, kiểm tra thiết lập IMDSv2 và hop limit của instance. Truy cập bằng cổng 80 theo security group của máy.

Khi S3 lỗi, ứng dụng đọc cả bộ CSV từ local. Khi Bedrock lỗi hoặc trả văn bản ngoài dữ liệu, bảng kết quả từ Python vẫn hiển thị. Không cần đưa credential vào Dockerfile hay image.

Xem [AWS Bedrock Converse](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-runtime/client/converse.html) và [Streamlit cache](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data).
