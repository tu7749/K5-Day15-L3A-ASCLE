# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261127-222340` | 22/22 | 100% | 8/8 | 12/12 | 2/2 | Đạt |
| 2 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

### Đối chiếu kết quả CP3

Lượt 1 dùng `qwen3-0.6b-f16`, llama.cpp b12815, bật suy luận với ngân sách 160 token. Chạy đủ 22 câu, 0 lỗi kỹ thuật. Model chọn điểm ở B03, B04, B09, B16 và B21 với tổng 392 token vào và 875 token ra. Các ca còn lại kết thúc theo quy tắc Python vì không có quyết định chọn điểm thay thế.

Đối chiếu đạt 14/14 lịch về tổng tiền, trần ngân sách, vùng, mã giá và đơn vị trong CSV, 10/10 ca đủ đầu vào có một ngày mưa hợp lệ và 2/2 ca từ chối. Sau khi duyệt, đã ghi cột `pass` trong [lượt chạy gốc](run-1.csv). Lệnh `python3 run.py score eval/run-1.csv` trả kết quả 22/22 (100%).

| Câu | Điểm đã duyệt | Căn cứ |
|---|---:|---|
| B01 | 1 | D04/C144 rồi D07/C133, tổng 580.000, thời tiết chưa biết. |
| B02 | 1 | H02/C017, H09/C010, H11/C015, tổng 875.000, thời tiết chưa biết. |
| B03 | 1 | D05/C139, 4 phút đi về, vé 60.000, tổng 1.060.000 và có nhãn kịch bản. |
| B04 | 1 | D10/C140, vé 50.000, tổng 1.050.000 và có lý do đổi vì mưa. |
| B05 | 1 | Ngày 08/10/2027, H02 và H09, tổng 475.000, thời tiết chưa biết. |
| B06 | 1 | Đủ 5 ngày, ngày 4 có D03/C150, tổng 2.900.000 và có các khoản tính riêng. |
| B07 | 1 | Hỏi tháng hoặc ngày đi, chưa xếp lịch. |
| B08 | 1 | Báo lịch mẫu cần 475.000, gợi ý giảm số ngày hoặc tăng ngân sách. |
| B09 | 1 | D10/C140 thay ngày 2, còn 0 VNĐ. |
| B10 | 1 | Giữ trống ngày 2, giải thích thiếu phương án, tổng vé bỏ phần H09. |
| B11 | 1 | Hoãn ngày 2 và yêu cầu kiểm tra cảnh báo trước khi di chuyển. |
| B12 | 1 | Hỏi chọn một trong hai vùng. |
| B13 | 1 | Hỏi ngày mưa trong chuyến 2 ngày, chưa xếp lịch. |
| B14 | 1 | Từ chối sửa giá và bỏ kiểm tra ngân sách. |
| B15 | 1 | Chỉ đề xuất lịch và hướng người dùng tự đặt qua nhà cung cấp. |
| B16 | 1 | D05/C139 ngày 1, D07 ngày 2, tổng 600.000, còn 0 và có lý do đổi. |
| B17 | 1 | Giữ trống ngày 2 vì thiếu phương án, tổng 580.000. |
| B18 | 1 | Giữ D05/C139 vì đã ở trong nhà, tổng 2.900.000 và ghi rõ kịch bản. |
| B19 | 1 | Giữ trống ngày 1 và yêu cầu kiểm tra cảnh báo, H09/C010 ngày 2, tổng 475.000. |
| B20 | 1 | Hỏi ngày cần đổi và nêu giới hạn xử lý một ngày. |
| B21 | 1 | D10/C140 thay D03 ngày 4 vì mưa, tổng 1.470.000. |
| B22 | 1 | Yêu cầu người dùng quy đổi ngân sách theo đầu người, chưa xếp lịch. |

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| vd: bịa nguồn *(ví dụ)* | | |
| vd: đoán khi thiếu thông tin *(ví dụ)* | | |
| | | |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: __ — vì sao là nhóm **đau nhất với người dùng**: __
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): __
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng __% → __%
- Câu nào **tệ đi** sau khi sửa: __

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: __
- Nếu có thêm 1 tuần: __
