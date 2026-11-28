# Chạy và triển khai Việt Du

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

Agent dòng lệnh cũng hỗ trợ gợi ý lưu trú. Chạy `python3 run.py` và nhập `Gợi ý khách sạn Đà Nẵng cho 2 người, 2 đêm, tối đa 500 nghìn/phòng/đêm` hoặc `Gợi ý chỗ ở Hà Giang cho 4 người, 2 đêm, tổng 1,8 triệu cho cả nhóm`. Agent dùng cận trên của giá ước tính để lọc các hạng tiết kiệm, vừa và thoải mái. Mỗi gợi ý ghi giá theo đơn vị, số phòng hoặc suất, tổng kỳ ở, độ tin cậy và nguồn.

Việt Du dùng Open-Meteo trực tiếp từ backend. Cho phép máy chủ truy cập `api.open-meteo.com` và `archive-api.open-meteo.com` qua HTTPS. Trình duyệt dùng nền bản đồ OpenStreetMap. Khi nền không tải được, các ghim và lịch trình vẫn hiển thị.

## EC2 với Docker

```bash
git clone https://github.com/tu7749/K5-Day15-L3A-ASCLE.git
cd K5-Day15-L3A-ASCLE
docker build -t viet-du .
docker run -d --name viet-du --restart unless-stopped \
  -p 80:8501 \
  -e AWS_REGION \
  -e S3_BUCKET \
  -e S3_PREFIX \
  -e BEDROCK_MODEL_ID \
  viet-du
```

Đặt biến môi trường ở shell EC2 trước khi chạy lệnh. `S3_BUCKET` và `BEDROCK_MODEL_ID` là tùy chọn. `S3_PREFIX` mặc định là `data`. Đặt cả bộ CSV dưới cùng prefix. Đính IAM role vào EC2 với quyền đọc đối tượng của prefix, liệt kê prefix để phát hiện tệp tùy chọn không có và `bedrock:InvokeModel` cho model đã duyệt. Nếu container chưa lấy được credential từ IAM role, kiểm tra thiết lập IMDSv2 và hop limit của instance. Truy cập bằng cổng 80 theo security group của máy.

Khi S3 lỗi, ứng dụng đọc cả bộ CSV từ local. Khi Bedrock lỗi hoặc trả văn bản ngoài dữ liệu, bảng kết quả từ Python vẫn hiển thị. Không cần đưa credential vào Dockerfile hay image.

### Bật Qwen3 trên EC2 Linux

Khởi động llama.cpp trên máy EC2 theo [hướng dẫn model](docs/connect-model.md) và giữ cổng model ở `127.0.0.1:8087`. Với Docker Engine trên Linux, dùng mạng host để web truy cập địa chỉ đó. Chạy lệnh dưới đây thay lệnh `docker run` ở trên khi cài một container mới.

```bash
docker run -d --name viet-du --restart unless-stopped --network host \
  -e MODEL_PROVIDER=llamacpp -e MODEL_NAME=qwen3-0.6b-f16 -e LLAMA_CPP_PORT=8087 \
  -e AWS_REGION -e S3_BUCKET -e S3_PREFIX -e BEDROCK_MODEL_ID viet-du
```

Trong container, `127.0.0.1` là chính container web, nên `--network host` là bắt buộc với cách trên. Nếu không dùng mạng host, đặt `LLAMA_CPP_HOST` là địa chỉ máy chạy llama.cpp. Khi đó llama.cpp phải nghe ở địa chỉ container truy cập được, ví dụ `--host 0.0.0.0` sau firewall, không mở cổng 8087 ra Internet.

### Docker Desktop (Windows/macOS)

Docker Desktop không hỗ trợ `--network host` như Linux. Chạy llama.cpp trên máy (hoặc container `ghcr.io/ggml-org/llama.cpp:server` publish `-p 127.0.0.1:8087:8087`) rồi trỏ web tới `host.docker.internal`:

```bash
docker run -d --name viet-du -p 8501:8501 \
  -e MODEL_PROVIDER=llamacpp -e MODEL_NAME=qwen3-0.6b-f16 \
  -e LLAMA_CPP_HOST=host.docker.internal -e LLAMA_CPP_PORT=8087 viet-du
```

`MODEL_NAME` phải trùng `--alias` của llama-server.

Streamlit phục vụ ở cổng `8501` của EC2. Kiểm tra `/_stcore/health`, sau đó thử tạo lịch ở ngày có dự báo mưa và các phương án hợp lệ để xác nhận giao diện hiện tên Qwen3 và số token.

Xem [AWS Bedrock Converse](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-runtime/client/converse.html) và [Streamlit cache](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data).
