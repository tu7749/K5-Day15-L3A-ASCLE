# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset · Địa điểm Đà Nẵng (`data/places_da_nang.csv`)

| | |
|---|---|
| Dùng để làm gì | nguồn địa điểm và giá vé cho planner khi `diem_den = da_nang`; chọn phương án thay thế khi mưa (`trong_nha`, `rui_ro_khi_mua`) |
| Từ đâu | nhóm tự tổng hợp từ trang du lịch / bán vé công khai (link từng dòng ở cột `nguon_gia`); tọa độ từ OpenStreetMap Nominatim |
| Xử lý những bước gì | chọn 15 điểm phổ biến · 5 điểm trong nhà để thay khi mưa · giá lấy vé người lớn ngoại tỉnh · nguồn lệch nhau thì ghi khoảng giá vào `ghi_chu` |
| Số dòng / số đoạn | 15 địa điểm (5 trong nhà) |
| Phiên bản / ngày lấy | v1 · 27/11/2026 · người làm: Nguyễn Đăng Doanh |
| Nhãn | thật (giá từ nguồn công khai); thời gian tham quan, mùa đẹp, mức rủi ro khi mưa: *(tự ước tính)* |
| Giới hạn | phần lớn nguồn giá là đại lý / blog, không phải trang chính thức; Bảo tàng Mỹ thuật dùng giá 2023 (đã đổi từ 10/6/2026, chưa có mức mới); Art in Paradise quy đổi từ USD; giờ mở cửa nhiều dòng `(chưa kiểm)` |

## Dataset 1 · [tên]

| | |
|---|---|
| Dùng để làm gì | nguồn cho công cụ `…` · bộ câu thử · đào bằng chứng |
| Từ đâu | data BTC cấp (`…` trong repo đề) · tài liệu khoá (trích / viết lại) · nhóm tự viết · sinh có seed |
| Xử lý những bước gì | lọc __ · làm sạch __ · ẩn danh __ · chia __ (script: `…`) |
| Số dòng / số đoạn | __ |
| Phiên bản / ngày lấy | __ |
| Nhãn | thật · `synthetic` |
| Giới hạn | thiếu gì, lệch về phía nào |

**Data `synthetic` (nhóm tự sinh):** ghi cách sinh (prompt / script), seed, người kiểm, số dòng đã kiểm tay. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · [tên]

…
