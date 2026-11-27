# Việt Du — Lập lịch Hà Giang và Đà Nẵng

Phiên bản 1.0.0

Việt Du là bản web Streamlit của nhóm ASCLE (AI20K khóa 5, L3A, Track C). Chọn điểm đến, ngày đi, số ngày, số khách và tổng ngân sách của cả nhóm. Kết quả gồm lịch theo ngày, bản đồ, gợi ý lưu trú và các khoản đã tính hoặc còn thiếu. Xem [thành viên](TEAMS.md) và [đặc tả hackathon](spec.md).

## Chạy website

Yêu cầu Python 3.10 trở lên. Tại thư mục chứa repo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make dev
```

Có thể chạy trực tiếp bằng `python -m streamlit run app.py`. Mở địa chỉ Local URL mà Streamlit in ra, mặc định `http://localhost:8501`. Website chạy khi chưa cấu hình khóa LLM. Nếu đã cấu hình Bedrock, phần tóm tắt được tạo từ dữ kiện đã kiểm tra. [Cách triển khai Docker và cấu hình dữ liệu](DEPLOY.md)

### Lập lịch trên website

Chọn điểm đến, ngày đi, số ngày, số khách và tổng ngân sách nhóm, rồi bấm **Tạo lịch trình**. Website lấy thời tiết từ Open-Meteo. Khi có dự báo mưa và ít nhất hai điểm trong nhà đủ dữ liệu giá và tuyến, [Qwen3 local](docs/connect-model.md) chọn điểm và giao diện hiện số token thực tế. Trên điện thoại, bấm **Bản đồ** để xem các ghim. [Video demo CP3](slides/demo-cp3-ui.mp4)

### Dữ liệu và các giới hạn

- Ba tệp lõi nằm trong `data/`: `places.csv`, `routes.csv`, `costs.csv`. Bộ nạp chỉ đọc UTF-8 hoặc UTF-8 BOM. Nối tuyến qua mã địa điểm, giữ đúng chiều và phương tiện. Hầu hết tuyến hiện có là tuyến ô tô một chiều. Thiếu chặng hoặc giờ mở cửa thì giao diện ghi rõ. Thời lượng thiếu dùng giả định có nhãn.
- `data/accommodations.csv` và `data/accommodation_prices.csv` nối bằng `accommodation_id`. Toàn bộ giá thiếu đơn vị hoặc sức chứa cần thiết chỉ hiện dưới dạng **Tham khảo từ …/đêm**. `data/accommodation_budget_bands.csv` cung cấp mức tham khảo tổng hợp khi có. Nếu bản clone thiếu các bảng lưu trú chi tiết, thêm các file đó vào `data/` hoặc cấu hình S3 theo hướng dẫn triển khai. [Kiểm kê dữ liệu](data_report.md)
- Chọn **Tùy chọn chuyến đi → Dự trù những khoản chưa có giá** để bổ sung khoản chi cho cả nhóm. Việt Du chỉ hiện **Trong ngân sách** khi mọi khoản phát sinh đã được tính hoặc dự trù. Các dòng `official_fee`, khoảng hiệu lực, nhóm thay thế và mã cùng khu được dùng khi CSV có trường tương ứng. Bảng hiện tại chưa có đầy đủ metadata này.
- Dự báo lấy từ Open-Meteo theo cụm điểm và múi giờ Việt Nam. Ngoài kỳ dự báo, lịch vẫn giữ nguyên và hiển thị tần suất mưa cùng tháng từ 5 năm đầy đủ gần nhất, dùng bộ dữ liệu ERA5. Khi API lỗi, lịch vẫn được trả và thời tiết ghi **Chưa có dữ liệu thời tiết**. [Tài liệu Open-Meteo](https://open-meteo.com/en/docs)
- Ảnh điểm đến minh họa do imagegen tạo, lưu dưới dạng WebP trong `static/assets/`. Ghim và đường nối trên Leaflet thể hiện thứ tự tham quan, với ghi công bản đồ OpenStreetMap.

### Kiểm tra

```bash
python run.py check
python -m pytest -q tests
```

`python run.py` vẫn mở bản thử CLI cho bộ đánh giá hackathon. Luồng web được kiểm tra riêng.

## Nhóm làm gì, khung làm gì

| Nhóm quyết định và viết | Khung làm sẵn (không cần sửa) |
|---|---|
| Người dùng, pain, bằng chứng, impact (`evidence/`, `spec.md` §1–§2) | — |
| Hình dạng giải pháp, công cụ, prompt, luồng (`spec.md` §4, `codebase/agent.py`, `tools.py`, `ai.py`) | Ghi mọi lần gọi model / công cụ vào trace, cộng token (`codebase/tracing.py`) |
| Bộ câu thử, metric, chuẩn "đạt" (`eval/benchmark.csv`, `eval/metric_spec.yaml`, `spec.md` §7) | Kiểm đủ cột, đủ câu `kho` / `tu_choi`, đủ ≥1/3 câu từ người dùng / data thật (`run.py check`) |
| Chấm cột `pass` theo metric spec | Chạy cả bộ một lệnh, có run ID, model, token từng câu (`run.py eval`) · tính % đạt (`run.py score`) |
| Persona, số người dùng thật, giá model (`cost/personas.yaml`) | Sinh ~50 phiên, chạy thật qua bản chạy thử, tính chi phí / phiên, / task thành công, / tháng 3 kịch bản (`run.py simulate`) |

## Chạy bản CLI trong 3 phút

Bản CLI dùng Python 3.10 trở lên. Các lệnh kiểm tra và bản web dùng thư viện trong `requirements.txt`.

**Bước 1 — Mở cửa sổ lệnh ngay trong thư mục repo**

| Windows (PowerShell) | macOS |
|---|---|
| Mở thư mục repo bằng File Explorer → bấm vào thanh địa chỉ → gõ `powershell` → Enter | Mở **Terminal** (Cmd + Space, gõ "Terminal") → gõ `cd ` (có dấu cách) → kéo thả thư mục repo vào → Enter |

Gõ `dir` (Windows) hoặc `ls` (macOS / Linux): thấy `run.py` và `README.md` là đang đứng đúng chỗ.

**Bước 2 — Kiểm Python và chạy thử**

| Việc | Windows (PowerShell) | macOS / Linux |
|---|---|---|
| Kiểm Python | `python --version` (không được thì `py --version`) | `python3 --version` |
| Chạy bản chạy thử (chế độ giả, chưa gọi model) | `python run.py` | `python3 run.py` |
| Kiểm bộ câu thử | `python run.py check` | `python3 run.py check` |

- Windows: gõ `python` mà mở Microsoft Store hoặc báo không có lệnh → dùng `py`. Chưa có Python: cài từ python.org, **tick "Add python.exe to PATH"**, mở lại PowerShell.
- macOS: báo `command not found: python` là bình thường → dùng `python3`.
- Bản CP3 dùng Qwen3 0.6B qua llama.cpp để chọn phương án đổi lịch khi mưa. Cấu hình chạy trên máy và không cần API key. [Hướng dẫn chạy model](docs/connect-model.md)

Trong README này lệnh viết là `python …`; máy nhóm cần `python3` hay `py` thì gõ thay.

## Lệnh

| Lệnh | Làm gì |
|---|---|
| `python run.py` | Chạy bản chạy thử (gõ đầu vào, nhận kết quả, kèm số lần gọi model / token) |
| `python run.py check` | Kiểm `eval/benchmark.csv` (6 cột, số câu, `kho` / `tu_choi`, mã `source`, ô trống, dòng mẫu) `eval/metric_spec.yaml` (≥3 metric điền đủ) và `TEAMS.md` (đúng format để BTC quét). Chỉ cảnh báo, không sửa file |
| `python run.py eval --try` | **Thử nối model:** chạy 3 câu đầu (`--try 5` = 5 câu) → `eval/run-try.csv`. Thấy "Nối model được" là xong. Không tính là một lượt |
| `python run.py eval` | Chạy cả bộ qua `codebase/agent.py` → `eval/run-1.csv` (lần sau `run-2.csv`…) + `traces/run-1.jsonl`. Mỗi dòng có run ID, model, số lần gọi model / công cụ, token. Model còn giả → chỉ ghi `run-mock.csv`; mọi câu lỗi → `run-error.csv`; Ctrl+C → `run-stopped.csv` — đều **không** được đánh số |
| `python run.py eval --fake` | Thử riêng bộ chạy, không gọi agent → `eval/run-fake.csv` |
| `python run.py score eval/run-1.csv` | Sau khi điền cột `pass` (1 / 0): in % đạt tổng và theo `type`. Còn ô trống → "CHƯA CHẤM XONG", không in % |
| `python run.py simulate --try` | Thử mô phỏng chi phí 10 phiên (làm trước CP3) → `cost/simulate-try.csv` |
| `python run.py simulate` | Mô phỏng chi phí khi dùng thật theo `cost/personas.yaml` (≥50 phiên) → `cost/simulate-N.csv` + `cost/simulate-N-summary.md` |
| `python run.py simulate --rate-from eval/run-2.csv` | Như trên, lấy tỉ lệ đạt từ đúng lượt chỉ định. Không ghi thì khung lấy lượt `run-N` mới nhất đã chấm, cùng model, và ghi rõ đã lấy lượt nào trong bản tóm tắt |

Gói miễn phí báo hết lượt: thêm `--wait 4` sau `eval` hoặc `simulate` (nghỉ 4 giây giữa hai lượt gọi). Sửa CSV bằng Excel: *File → Save As → CSV UTF-8*; Google Sheets: *Tệp → Tải xuống → CSV*.

**Lượt có lỗi kỹ thuật** (cột `error` có chữ): không sửa tay file đó, chạy lại thành lượt mới và ghi vào bảng các lượt ở `eval/README.md`. Không xoá file lượt nào.

## Bản chạy thử — viết ở đâu

| File | Viết gì | Bước guide |
|---|---|---|
| `codebase/agent.py` | `answer(text)` — luồng chính, đúng hình dạng ở `spec.md` §4. Khung có sẵn một workflow 2 bước *ví dụ* | 3.2 |
| `codebase/tools.py` | Công cụ của bài toán, mỗi công cụ một hàm có `@tool` | 2.2, 3.2 |
| `codebase/ai.py` | `call_model(system, user)` gọi API nội bộ của llama.cpp và lấy token từ `usage`. Lệnh mặc định vẫn hỗ trợ chạy khung với model giả. | 3.3 |

- **Trước CP2:** để chế độ giả, công cụ trả dữ liệu giả — `python run.py` đi hết luồng là đủ.
- **Trước CP3:** nối model thật theo [docs/connect-model.md](docs/connect-model.md), `eval --try` thấy token > 0 rồi mới `eval`.
- Bộ chạy gửi **nguyên ô `input`** của câu thử vào `answer(text)`. Dữ liệu địa điểm, giá, cung đường và thời tiết dự kiến để trong `data/` và được truy xuất theo điểm đến. Nhóm sẽ ghi nguồn và cách xử lý trong [data card](data/DATA_CARD.md).

## Phần nào thật, phần nào giả

| Thành phần | Thật / Giả | Ghi chú |
|---|---|---|
| Lời gọi AI ở quyết định trung tâm | Qwen3 0.6B | Chọn mã điểm thay thế trong danh sách đã qua kiểm tra. |
| Dữ liệu địa điểm, giá, cung đường và thời tiết | CSV của Hà Giang và Đà Nẵng | CLI nhận thời tiết giả lập từ đầu vào. Bản web có luồng Open-Meteo riêng. |

## Dùng AI vào việc gì

Nhóm dùng Codex để điền hồ sơ CP1, diễn đạt lát cắt và đồng bộ tài liệu. Ở CP3, Codex hỗ trợ tích hợp model local, mở rộng benchmark và soạn bản nháp đối chiếu kết quả. [Hồ sơ dùng AI](docs/ai-usage.md) · [Quy ước làm việc](AGENTS.md)

## File mẫu — điền ở bước nào

| File | Điền ở bước guide | Mốc |
|---|---|---|
| `TEAMS.md` | 1.0 | CP1 · **đúng format**, BTC quét khi chấm |
| `canvas.md` | 1.4 | CP1, cập nhật CP2 |
| `evidence/hypothesis.md` | 1.1 | trước khi tìm bằng chứng |
| `evidence/data-mining.md` · `evidence/interviews/TEMPLATE.md` → `P1.md`… · `evidence/survey/TEMPLATE.md` | 1.2 | bắt đầu sau Zoom, xong CP3 |
| `evidence/summary.md` | 1.2 | CP3 |
| `spec.md` | §0–§2: 1.1–1.3 · §3–§5: 2.1–2.3 · §7: 2.4 · §8: 4.2 · §10: suốt | §7 chốt CP2 · §0–§7 CP3 · đủ CP4 |
| `data/DATA_CARD.md` | 2.4 | bản đầu CP2 |
| `eval/benchmark.csv` · `eval/metric_spec.yaml` | 2.4 | ≥10 câu + metric chốt CP2 · 20–30 câu CP3 |
| `codebase/` | 3.2, 3.3 | khung CP2 · AI thật CP3 |
| `eval/report.md` · `eval/README.md` | 4.1 (README mục 1–4 từ 2.4) | CP4 |
| `cost/personas.yaml` · `cost/cost-estimate.md` | 4.2 | thử 10 phiên CP3 · đủ CP4 |
| `validation/log.md` *(bonus)* | 4.3 | CP4 |
| `slides/outline.md` → `demo-slides.pdf` | 5.1 | CP4 |
| `reflection/TEMPLATE.md` → `reflection/<ten>.md` | 5.3 | 23:59 Thứ Bảy 28/11 |
| `AGENTS.md` · `docs/ai-usage.md` | khi dùng coding agent / AI | suốt |

## Bảy hạng mục bắt buộc — nằm ở file nào

| # | Hạng mục | File |
|---|---|---|
| 1 | Bằng chứng pain | `evidence/` (tổng hợp ở `evidence/summary.md`) |
| 2 | Impact có số | `spec.md` §2 |
| 3 | Thiết kế giải pháp | `spec.md` §4 |
| 4 | Bản chạy thử làm trọn lát cắt | `codebase/` · lệnh ở mục "Lệnh" |
| 5 | Định nghĩa "tốt" + bộ câu thử | `data/DATA_CARD.md` · `eval/` |
| 6 | Mô phỏng chi phí khi dùng thật | `cost/` |
| 7 | Slide + demo + video dự phòng | `demo-slides.pdf` ở thư mục gốc · video dự phòng sẽ cập nhật ở CP4 |
| + | *Bonus:* người dùng thử | `validation/log.md` |
