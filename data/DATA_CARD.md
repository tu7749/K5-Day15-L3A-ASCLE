# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Bổ sung · 15 địa điểm Đà Nẵng (Doanh, ghép vào `places.csv` / `costs.csv` của Sơn)

| | |
|---|---|
| Dùng để làm gì | điền chỗ trống cho 15 điểm Đà Nẵng phổ biến để planner xếp lịch và đổi lịch khi mưa |
| Từ đâu | trang du lịch / bán vé công khai, link ở cột `nguon` của `costs.csv` C212–C220 |
| Xử lý những bước gì | **chỉ điền ô trống**, không ghi đè số Sơn đã có (kiểm bằng script so từng ô) · `thoi_luong_phut`, `mua_dep` cho 15 điểm · `loai = trong_nha` cho chợ Hàn, chợ Cồn · 9 dòng giá vé mới · mức rủi ro khi mưa ghi vào `ghi_chu` |
| Số dòng | 15 dòng `places.csv` sửa · 9 dòng `costs.csv` thêm |
| Phiên bản / ngày lấy | 27/11/2026 · Nguyễn Đăng Doanh |
| Nhãn | giá vé: thật (nguồn công khai); thời lượng, mùa đẹp, rủi ro khi mưa: *(tự ước tính)* |
| Giới hạn | nguồn giá phần lớn là đại lý / blog; Art in Paradise quy đổi từ 7.59 USD; vé miễn phí (biển, chợ, đèo, nhà thờ) là *(tự ước tính)* vì không có nguồn ghi "miễn phí" |

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
