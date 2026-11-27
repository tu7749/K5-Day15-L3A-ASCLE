# Data card · ASCLE · CP2

Hai mã vùng là `ha_giang` và `da_nang`. Bản chạy thử đọc CSV local, chọn dữ liệu theo mã vùng và giữ mã nguồn từng khoản giá trong kết quả.

| Dataset | Dòng Hà Giang / Đà Nẵng | Nguồn, phiên bản và cách dùng |
|---|---:|---|
| [places.csv](places.csv) | 145 / 217 | Tổng 362 dòng. Tọa độ theo trường `nguon_toa_do` (chẳng hạn OpenStreetMap Nominatim), mã và ghi chú theo từng dòng. Bản có trong commit `c01ee13`. Chỉ dùng danh sách điểm đã chọn trong cấu hình CP2, có tuyến đi và giá vé khớp bảng giá. |
| [costs.csv](costs.csv) | 64 / 111 | Tổng 175 dòng. Bảng giá tham khảo nhóm tổng hợp từ trang công khai. URL, ngày trang và ngày kiểm tra nằm trên từng dòng nếu có. Bản `c01ee13`. Kiểm mã, vùng, hạng mục và đơn vị. Dùng `gia_max_vnd` để ước tính, bỏ mục thiếu mức tối đa hoặc có đơn vị khác, đối chiếu mã điểm và giá vé với `places.csv`. |
| [routes.csv](routes.csv) | 31 / 14 | Tổng 45 dòng, gồm cặp điểm OSRM ô tô trên bản đồ OSM và tư liệu bài viết. Bản `c01ee13`. Chỉ lấy cạnh OSRM có đủ hai mã điểm và số phút. Dùng cùng ước tính cho chiều về, tính tuyến ngắn nhất từ căn cứ và loại lượt đi về trên 180 phút. |
| Kịch bản thời tiết | Một ngày trong một yêu cầu | `synthetic` khi nhập kịch bản demo. Người dùng chỉ định ngày mưa hoặc cảnh báo, phép xử lý cố định và không cần seed. Nếu thiếu kịch bản, trạng thái là chưa có dữ liệu. CP2 chưa gọi API dự báo. |

CSV là dữ liệu công khai do nhóm tổng hợp với độ bao phủ và cách đo khác nhau theo trường. Chỗ thiếu trong bảng vé, nhãn trong nhà, tuyến và giờ đến không được suy thành dữ liệu có thật. CP2 chỉ xếp một hoạt động chính mỗi ngày, không khẳng định giờ mở cửa, đường an toàn, chỗ còn hoặc giá hiện hành. Bảo tàng có tuyến và giá là ứng viên ngày mưa ở Đà Nẵng. Hà Giang chưa có ứng viên trong nhà đạt điều kiện của CP2, hang động không được dùng thay thế khi mưa.

**Đơn vị ngân sách.** Giá được tính mỗi người, tối đa một suất ở và một xe thuê mỗi người theo mã giá đã chọn, cộng vé. Tiền ăn, xăng và di chuyển đến điểm xuất phát tính riêng. Không suy ra giá một người từ giá phòng khi chưa biết số người chia. Các bảng lưu trú bổ sung chưa được dùng trong bản CP2.

**Bằng chứng người dùng.** Tập bài hỏi đáp được mã hoá ở [evidence/data-mining.md](../evidence/data-mining.md), tách khỏi dữ liệu vận hành.

**Bổ sung sau `c01ee13` · 15 điểm Đà Nẵng (Nguyễn Đăng Doanh, 27/11/2026).** Chỉ điền ô trống, không ghi đè giá trị đã có (đã so từng ô bằng script).

| File | Thay đổi | Nhãn |
|---|---|---|
| `places.csv` | 15 dòng Đà Nẵng (D01, D03–D09, D11–D13, D15, D16, DO144, DO193): thêm `thoi_luong_phut`; `loai = trong_nha` cho chợ Hàn, chợ Cồn; `ve_vnd` + `ve_cost_id` còn trống; `ghi_chu` thêm "rủi ro khi mưa: …" và "mùa đẹp tự ước tính: …" (để trống `mua_dep` vì planner loại điểm khỏi các tháng không có trong cột này) | thời lượng, mùa đẹp, rủi ro khi mưa: *(tự ước tính)* |
| `costs.csv` | thêm C212–C220 (Đà Nẵng còn 120 dòng): vé Art in Paradise, Sun Wheel, suối khoáng Núi Thần Tài kèm URL nguồn; các điểm miễn phí (biển, chợ, đèo, nhà thờ, đỉnh Bàn Cờ) | giá có URL: thật · vé 0đ của điểm công cộng: *(tự ước tính)* · Art in Paradise quy đổi từ 7.59 USD |
