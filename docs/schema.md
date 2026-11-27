# Schema dữ liệu: giao diện (C) · planner (B) · data địa điểm (A)

> Mốc "Chốt schema" (giờ 2 trong `Trinh_tu_lam_viec_24h.xlsx`). Đã thống nhất: Doanh (C), Tú (B), Sơn (A) — 27/11/2026.
> Đổi tên trường hay thêm trường bắt buộc thì báo cả ba người và sửa file này cùng lúc với code.
> Ví dụ đầy đủ: [`ui/mock_plan.json`](../ui/mock_plan.json). Code kiểm: `ui/validate.py` (`validate_input`, `check_plan`).

## 1. Hàm planner

```python
# codebase/planner.py  (B viết)
def make_plan(req: dict) -> dict: ...
```

- Giao diện (`streamlit_app.py`) gọi thẳng `make_plan(req)` để có JSON hiển thị.
- Khung chấm (`run.py eval`, `simulate`) chỉ gọi `answer(text)` trong `codebase/agent.py`: `answer()` tách thông tin từ câu chữ → gọi `make_plan()` → trả `{"output": <văn bản>}`.
- Chưa có `planner.py` thì giao diện đọc `ui/mock_plan.json` và ghi rõ "dữ liệu giả".
- Lỗi do người dùng (ngân sách quá thấp, không có phương án…) trả `ok: false` + `error`, **không** raise. Lỗi hệ thống (API thời tiết, Bedrock) được raise, giao diện tự bắt.

## 2. Đầu vào `req`

Giao diện đã kiểm hợp lệ trước khi gọi (`validate_input`), planner không cần kiểm lại kiểu dữ liệu.

| Trường | Kiểu | Ràng buộc | Ví dụ |
|---|---|---|---|
| `diem_den` | str | `ha_giang` · `da_nang` (phạm vi mới từ commit 19b4e66) | `"da_nang"` |
| `so_ngay` | int | 1–5 | `3` |
| `ngan_sach_moi_nguoi` | int | VND, > 0, ≤ 100.000.000 | `3000000` |
| `ngay_di` | str | `YYYY-MM-DD`, từ hôm nay đến ≤ 1 năm | `"2026-12-10"` |
| `so_nguoi` | int | 1–20 | `4` |
| `phong_cach` | str | `tiet_kiem` · `vua` · `thoai_mai` | `"vua"` |

## 3. Đầu ra

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `ok` | bool | có | `false` = không xếp được lịch |
| `error` | str \| null | có | câu báo cho người dùng khi `ok: false`, vd "Ngân sách tối thiểu cho 3 ngày là 1.800.000đ/người" |
| `days` | list | khi `ok` | mỗi phần tử một ngày, xem 3.1 |
| `cost_breakdown` | dict[str, int] | khi `ok` | khoá: `cho_o`, `an_uong`, `di_lai`, `ve`, `du_phong` (VND / người) |
| `total_per_person` | int | khi `ok` | = tổng `cost_breakdown`; ≤ `budget_per_person` |
| `budget_per_person` | int | khi `ok` | chép lại từ `req` |
| `text` | str \| null | không | bản diễn đạt từ LLM (`llm.py` của D); `null` khi Bedrock lỗi hoặc không dùng |
| `input` | dict | không | chép lại `req`, để debug |

### 3.1 Một ngày (`days[i]`)

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `day` | int | 1, 2, 3… |
| `date` | str | `YYYY-MM-DD` |
| `weather` | dict | `rain_prob` (float 0–1), `condition` (`nang` · `may` · `mua`), `temp_c` (số) — lấy từ `get_weather()` của A |
| `slots` | dict | khoá `sang`, `chieu`, `toi`; mỗi khoá là list hoạt động, xem 3.2; buổi trống = `[]` |
| `changed_because` | str \| null | lý do đổi lịch vì mưa; `null` = không đổi |
| `warnings` | list[str] | cảnh báo an toàn (đèo trơn, sạt lở…); không có = `[]` |
| `original_slots` | dict | *(tuỳ chọn)* lịch trước khi đổi, cùng dạng `slots` — giao diện hiện "Trước → Sau" |

### 3.2 Một hoạt động

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `place_id` | str | đúng `id` trong file địa điểm (mục 5) |
| `name` | str | tên hiển thị |
| `cost` | int | VND / người |
| `indoor` | bool | `true` = trong nhà, dùng được khi mưa |

## 4. Quy ước chung

- Tiền luôn là **int VND / người**, không phải chuỗi đã định dạng. Giao diện tự định dạng `3.000.000đ`.
- Mọi số tiền và địa điểm phải đến từ data của A, không do LLM sinh ra (B kiểm ở `validate_output()`).
- Giao diện **không tự tính** tiền hay xếp lịch, chỉ hiển thị.

## 5. File địa điểm (`data/places_*.csv`) — *đề xuất, chờ Sơn (A) xác nhận*

Mỗi điểm đến một file cùng cột: `data/places_da_nang.csv` (Doanh), Hà Giang (Sơn). Planner đọc file theo `req["diem_den"]`.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | str | `DN01`… (Đà Nẵng), `HG01`… (Hà Giang) — duy nhất |
| `diem_den` | str | `da_nang` · `ha_giang` |
| `ten` | str | tên hiển thị |
| `khu_vuc` | str | quận / huyện, để gom các điểm gần nhau vào một buổi |
| `lat`, `lon` | float | tọa độ, lấy từ OpenStreetMap (Nominatim) |
| `trong_nha` | 0/1 | 1 = dùng được khi mưa |
| `thoi_gian_tham_quan_gio` | float | *(tự ước tính)* |
| `ve_vnd` | int | vé người lớn / người; miễn phí = 0 |
| `gio_mo_cua` | str | ghi `(chưa kiểm)` nếu chưa có nguồn |
| `mua_dep` | str | tháng đẹp; không có nguồn thì ghi `(tự ước tính)` |
| `rui_ro_khi_mua` | `thap` · `tb` · `cao` | `cao` = không xếp vào ngày mưa (đèo, biển, cáp treo) |
| `nguon_gia` | str | link nguồn giá, hoặc `(tự ước tính: lý do)` |
| `ngay_xem` | str | ngày xem nguồn `YYYY-MM-DD` |
| `ghi_chu` | str | điều kiện giá, giới hạn |
