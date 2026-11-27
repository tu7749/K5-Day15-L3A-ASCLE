# Báo cáo kiểm tra dữ liệu · Bước 0

Kiểm tra snapshot local ngày 27/11/2026, giờ Việt Nam. Số dòng tính theo bản ghi CSV, bỏ dòng tiêu đề.

**Kết luận ban đầu của bước 0.** File `data/lodging.csv` chưa có và ba CSV chính dùng tên cột khác schema. Sau khi nhóm xác nhận dùng lớp ánh xạ chỉ đọc, các bảng hiện có đã được ánh xạ và qua kiểm schema. Số liệu chuẩn hóa nằm ở mục 6.

## 1. Tệp, số dòng và schema

| Tệp | Hà Giang | Đà Nẵng | Tổng |
|---|---:|---:|---:|
| `places.csv` | 145 | 217 | 362 |
| `costs.csv` | 64 | 111 | 175 |
| `routes.csv` | 31 | 14 | 45 |
| `lodging.csv` | — | — | Thiếu file |
| `accommodations.csv` | 204 | 194 | 398 |
| `accommodation_prices.csv` | 154 | 156 | 310 |
| `accommodation_budget_bands.csv` | 14 | 12 | 26 |

| Tệp | Cột bắt buộc thiếu theo tên |
|---|---|
| `places.csv` | `place_id`, `region`, `name`, `setting`, `duration_hours`, `ticket_vnd`, `best_months`, `category`, `source`, `source_date` |
| `costs.csv` | `cost_id`, `region`, `category`, `item`, `unit`, `price_min_vnd`, `price_max_vnd`, `notes`, `source`, `source_date` |
| `routes.csv` | `from_place_id`, `to_place_id`, `distance_km`, `duration_min`, `mode`, `note` |
| `lodging.csv` | Thiếu toàn bộ vì file chưa có. `lodging_id`, `region`, `name`, `type`, `area`, `lat`, `lon`, `price_min_vnd`, `price_max_vnd`, `price_unit`, `capacity_persons`, `rating`, `tier`, `source`, `source_date` |

Một số cột có thể ánh xạ sau khi thống nhất hợp đồng, như `id → place_id`, `thanh_pho → region`, `nguon → source`, `ngay_kiem → source_date`. Chuyển tên cột không bổ sung dữ liệu còn thiếu. Chẳng hạn `routes.csv` có khoảng phút và loại nguồn, trong khi schema mới cần một thời lượng và chế độ di chuyển cho mỗi tuyến.

## 2. Ô trống và nguồn

| Tệp | Các cột có ô trống và số bản ghi tương ứng |
|---|---|
| `places.csv` | `lat` × 13, `lon` × 13, `loai` × 316, `loai_osm` × 16, `thoi_luong_phut` × 362, `ve_vnd` × 347, `ve_cost_id` × 347, `mua_dep` × 359, `nguon_toa_do` × 13, `ghi_chu` × 281 |
| `costs.csv` | `place_id` × 131, `gia_max_vnd` × 6, `ngay_trang` × 8, `ghi_chu` × 30, `gio_mo_cua` × 146 |
| `routes.csv` | `tu_id` × 4, `den_id` × 3, `phut_min` × 10, `phut_max` × 10, `ngay_trang` × 28 |
| `accommodations.csv` | `locality` × 7, `source_property_type` × 7, `stars` × 271, `latitude` × 311, `longitude` × 311, `coordinate_method` × 311, `coordinate_source_url` × 311, `street_address` × 323, `nearest_place_id` × 314, `distance_to_nearest_place_km_air` × 314, `amenities` × 206, `reference_from_vnd` × 105, `reference_to_vnd` × 357, `reference_price_unit` × 105, `budget_tier` × 105, `price_source_url` × 105 |
| `accommodation_prices.csv` | `room_type` × 287, `price_to_vnd` × 269, `adults_per_unit` × 299, `sample_check_in` × 304, `sample_check_out` × 304, `price_updated_at` × 240 |
| `accommodation_budget_bands.csv` | — |

| Tệp | Trống nguồn | Trống ngày | Ngày lỗi hoặc ở tương lai | Quá 90 ngày |
|---|---:|---:|---:|---:|
| `places.csv` | 13 | 0 | 0 | 0 |
| `costs.csv` | 0 | 0 | 0 | 0 |
| `routes.csv` | 0 | 0 | 0 | 0 |
| `accommodations.csv` | 105 | 0 | 0 | 0 |
| `accommodation_prices.csv` | 0 | 0 | 0 | 0 |

Độ mới trong bảng trên dựa vào ngày kiểm tra ghi trong file. Ngày này có thể khác ngày công bố hoặc cập nhật giá. Bảng tổng hợp `accommodation_budget_bands.csv` có phương pháp và ngày kiểm tra, không có nguồn giá riêng từng dòng.

## 3. Giá, tọa độ và liên kết tuyến

Sàng lọc giá theo vùng, loại và đơn vị. Lấy trung điểm khi có đủ hai đầu khoảng, dùng cận dưới để rà soát riêng nếu thiếu cận trên. Gắn cờ khi nhỏ hơn 1/5 hoặc lớn hơn 5 lần trung vị của nhóm có ít nhất 5 giá dương. Ngưỡng này chỉ dùng cho đợt rà soát. Vé miễn phí được giữ ở mức 0 và không đưa vào phép so với trung vị dương.

| Tệp | Giá âm / cận dưới lớn hơn cận trên / sai cú pháp | Thiếu một hoặc hai cận | Lệch trung vị |
|---|---|---:|---|
| `costs.csv` | âm: 0; đảo cận: 0; sai cú pháp: 0 | 6 | 10 (`C041`, `C028`, `C125`, `C126`, `C127`, `C150`, `C151`, `C152`, `C154`, `C166`) |
| `accommodations.csv` | âm: 0; đảo cận: 0; sai cú pháp: 0 | 357 | 20 (`slt_5600`, `slt_5555`, `slt_5550`, `slt_5622`, `slt_3460`, `slt_3461`, `slt_5548`, `slt_5562`, `slt_5588`, `slt_5549`, `slt_5642`, `slt_5563`…) |
| `accommodation_prices.csv` | âm: 0; đảo cận: 0; sai cú pháp: 0 | 269 | 21 (`lodging_price_0038`, `lodging_price_0044`, `lodging_price_0084`, `lodging_price_0237`, `lodging_price_0238`, `lodging_price_0252`, `lodging_price_0253`, `lodging_price_0254`, `lodging_price_0255`, `lodging_price_0256`, `lodging_price_0257`, `lodging_price_0258`…) |

Giá vé trong `places.csv`: 15 dòng có giá, 347 dòng trống, 0 dòng có giá âm hoặc sai định dạng số nguyên không âm. Các giá lệch trung vị là cờ để rà nguồn, có thể phản ánh hạng dịch vụ khác.

Kiểm tọa độ bằng hộp giới hạn thăm dò (tự ước tính cho bộ dữ liệu này, không phải ranh giới hành chính). Hà Giang: vĩ độ 22,1–23,5 và kinh độ 104,1–105,7. Đà Nẵng và vùng lân cận trong bộ dữ liệu: vĩ độ 15,2–16,35 và kinh độ 107,45–109,0.

- `places.csv` có 13 dòng thiếu tọa độ và 0 dòng ngoài hộp hoặc sai định dạng.
- `accommodations.csv` có 311 dòng thiếu tọa độ và 0 dòng ngoài hộp hoặc sai định dạng.
- `routes.csv` có 6 dòng trống ít nhất một đầu tuyến, 10 dòng thiếu ít nhất một cận thời lượng và 0 dòng thiếu khoảng cách. Mã đầu tuyến đã điền nhưng không có trong `places.csv`: —. Số lượt đầu tuyến lệch vùng: 0.

## 4. Lưu trú và mức giá

Ba tệp bổ sung có cấu trúc danh mục, giá chi tiết và tổng hợp theo vùng. Các nhãn trong danh mục là dải giá niêm yết gốc. Schema yêu cầu ba mức `budget`, `mid`, `comfort` cho mỗi vùng.

| Vùng | Dải giá niêm yết trong danh mục | Đơn vị ở bảng giá chi tiết | Số cơ sở có ≥1 dòng đủ cả hai cận giá, đơn vị phòng/giường, sức chứa và nguồn |
|---|---|---|---:|
| `ha_giang` | `trống` × 58, `250k_to_under_500k` × 74, `500k_to_under_1m` × 31, `under_250k` × 26, `1m_to_under_2m` × 12, `2m_plus` × 3 | `package_guest_unspecified_nights` × 1, `package_room_unspecified_nights` × 1, `room_night` × 5, `bed_night` × 1, `night_unspecified` × 146 | 0 |
| `da_nang` | `under_250k` × 29, `250k_to_under_500k` × 73, `trống` × 47, `500k_to_under_1m` × 20, `1m_to_under_2m` × 10, `2m_plus` × 15 | `night_unspecified` × 150, `bed_night` × 3, `room_night` × 3 | 0 |

Giá chi tiết liên kết với danh mục qua `accommodation_id`. Có 0 dòng không tìm thấy danh mục. `night_unspecified` chưa xác định đơn vị giá là phòng hay người/giường. Cả 12 dòng có đơn vị rõ là `room_night` hoặc `bed_night` đều thiếu cận trên. `stars` là hạng sao được lưu, chưa có trường đánh giá của khách theo schema.

**Cảnh báo mức giá.** Chưa có dòng nào mang sẵn nhãn `budget`, `mid` hoặc `comfort` ở cả hai vùng. Chưa thể xác nhận đủ 8 dòng mỗi mức. Ngay cả khi chuyển nhãn dải giá, tập có đủ đơn vị, khoảng giá và sức chứa vẫn nhỏ hơn 24 cơ sở mỗi vùng.

## 5. Quyết định sau bước 0

- Nhóm xác nhận dùng bộ cột hiện có qua lớp ánh xạ chỉ đọc, dùng cấu hình thời lượng theo loại khi chưa có giá trị nguồn và gắn cờ ước tính.
- Hai bảng lưu trú được nối theo mã. Giá một cận dùng chính giá nguồn ở cả hai cận. Khi đơn vị chưa rõ, áp dụng điều kiện theo loại cơ sở và giới hạn độ tin cậy ở mục 6.
- `weather.py` sẽ do nhóm cung cấp. Bản Streamlit trả trạng thái chưa có dữ liệu và bộ kiểm thử dùng mock.

## 6. Ánh xạ đang dùng

| Schema chuẩn | Nguồn và quy tắc |
|---|---|
| Địa điểm | `places.csv`: mã, vùng, tên, tọa độ và phí vé đọc từ `id, thanh_pho, ten, lat, lon, ve_vnd`. `loai` cho môi trường, `loai_osm` cho nhóm có thể nhận diện. `thoi_luong_phut` đổi sang giờ, ưu tiên ghi đè từ `duration_overrides.csv` rồi mới dùng mặc định theo nhóm. `mua_dep` chỉ nhận danh sách tháng phân tách bằng dấu chấm phẩy. `nguon_toa_do, ngay_kiem` giữ xuất xứ tọa độ. Vé có mã bảng giá thì đối chiếu `ve_cost_id` với dòng giá cùng vùng và địa điểm. |
| Chi phí | `costs.csv`: `id, thanh_pho, hang_muc, mo_ta, don_vi, gia_min_vnd, gia_max_vnd, ghi_chu, nguon, ngay_kiem` sang mã, vùng, loại, tên, đơn vị, hai cận, ghi chú và nguồn. Đơn vị giữ cả cơ sở tính người, xe, phòng hoặc giường nếu có. Các hàng thiếu cận hoặc đơn vị chưa hỗ trợ được ghi vào thống kê loại. |
| Tuyến | `routes.csv`: `tu_id, den_id, km, phut_max, loai_so, ghi_chu, nguon, ngay_kiem`. Chỉ bộ tuyến có chế độ đã xác định mới dùng làm thời lượng. `osrm_oto` ánh xạ thành ô tô. Giữ hai chiều độc lập khi có đủ, đánh dấu giả định đối xứng khi chỉ có một chiều. |
| Lưu trú | Ưu tiên `lodging.csv` chuẩn nếu có. Bộ dữ liệu hiện tại dùng `accommodations.csv` nối `accommodation_prices.csv` bằng `accommodation_id`; lấy vùng, loại và tọa độ từ danh mục, hai cận, đơn vị, sức chứa, URL và ngày kiểm từ bảng giá. Giá danh mục được dùng khi cơ sở không có bản ghi chi tiết. Dải giá tổng hợp theo vùng không dùng để suy ra giá một cơ sở. |

Tên cột và bảng chuyển đổi giá trị nằm trong [data_adapter.py](data_adapter.py). Chỉ lấy hai vùng được hỗ trợ. Snapshot hiện tại không có dòng ngoài hai vùng, còn các dòng bị loại vì lý do khác được đếm khi chạy `python3 validate_data.py`.

### Đếm đơn vị và xử lý độ tin cậy

| Vùng | Phòng / giường / không rõ / gói (giá chi tiết) | Suy ra giá tính theo phòng ở hotel hoặc guesthouse | Đơn vị vẫn chưa rõ trong bộ chuẩn | Giá một mức | Hạ độ tin cậy thực tế |
|---|---:|---:|---:|---:|---:|
| Hà Giang | 5 / 1 / 146 / 2 | 79 | 61 | 129 | 135 |
| Đà Nẵng | 3 / 3 / 150 / 0 | 122 | 24 | 128 | 142 |

Đơn vị không rõ của Hà Giang trong bộ chuẩn gồm 59 dòng homestay ghi `night_unspecified` và 2 dòng gói. Đà Nẵng có 24 dòng homestay ghi `night_unspecified`. Danh mục gốc có 58 ô đơn vị trống ở Hà Giang (12 hotel, 23 guesthouse, 22 homestay, 1 hostel) và 47 ở Đà Nẵng (39 guesthouse, 8 homestay). Bảng giá chi tiết không có ô đơn vị trống. Bộ chuẩn loại 12 hàng kiểu hostel ở Hà Giang và 4 ở Đà Nẵng vì schema chỉ nhận hotel, guesthouse và homestay. Có thể trùng nhóm giữa các cột. Số hạ độ tin cậy so với quy tắc chỉ xét tuổi dữ liệu và độ rộng giá, tại ngày 27/11/2026. Sau áp giới hạn có 85 dòng thấp và 210 dòng vừa trên 295 dòng lưu trú đã ánh xạ.

### Số dòng dùng sau ánh xạ

| Vùng | Địa điểm (có tọa độ) | Chi phí | Tuyến | Giá lưu trú (có tọa độ) |
|---|---:|---:|---:|---:|
| Hà Giang | 145 (138) | 53 | 14 | 143 (33) |
| Đà Nẵng | 217 (211) | 101 | 14 | 152 (43) |

- **Hà Giang:** địa điểm gồm 3 viewpoint, 1 culture, 1 nature, 1 market, 2 activity, 137 other. Giá lưu trú gồm 67 hotel, 12 guesthouse, 64 homestay. Chi phí gồm 14 vé, 10 lưu trú dự phòng, 9 ăn uống, 6 hoạt động, 5 đi liên tỉnh, 5 thuê xe máy, 1 thuê ô tô, 1 xăng, 2 khác.
- **Đà Nẵng:** địa điểm gồm 1 viewpoint, 5 culture, 3 nature, 2 market, 1 activity, 205 other. Giá lưu trú gồm 117 hotel, 11 guesthouse, 24 homestay. Chi phí gồm 71 vé, 20 đi liên tỉnh, 4 thuê xe máy, 1 lưu trú dự phòng, 1 ăn uống theo chuyến, 4 khác.
- Cả 28 tuyến dùng khi ánh xạ là ô tô, với tọa độ tra qua mã địa điểm. Giá lưu trú đếm theo dòng giá, tương ứng 140 cơ sở ở Hà Giang và 143 ở Đà Nẵng.
