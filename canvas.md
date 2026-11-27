# Canvas — ASCLE · Track C (Du lịch)

> Điền ở guide bước 1.4. CP1 17:00 Thứ Sáu 27/11: nộp bản đầu, đủ 7 dòng (dòng 4 được ghi giả thuyết + nguồn sẽ kiểm).
> CP2 19:30 Thứ Sáu 27/11: cập nhật (số bằng chứng đầu, lát cắt đã chốt) và điền dòng "Đã đổi gì so với CP1".
> Track F: chép thêm thẻ đề của nhóm (khung trong file track F) xuống dưới bảng này.

| # | Dòng | Nhóm điền |
|---|---|---|
| 1 | Track + lát cắt dự kiến | Track C – Du lịch. Lên lịch chuyến Hà Giang tự túc 2–5 ngày theo ngân sách và đề xuất hoạt động thay thế cho một ngày có mưa. |
| 2 | Người dùng chính (một vai cụ thể — không phải "học viên nói chung") | Người đứng ra lên lịch chuyến đi Hà Giang tự túc cho nhóm bạn. |
| 3 | Pain một câu: ai — đang làm gì — vướng đâu — hậu quả | Người lên lịch Hà Giang cho nhóm bạn phải đối chiếu chi phí, cung đường và thời tiết từ nhiều nguồn nên tốn thời gian xếp lại lịch và tính lại tiền khi hoạt động ngoài trời gặp mưa. |
| 4 | Bằng chứng đầu — CP1: giả thuyết + nguồn sẽ kiểm · CP2: số đầu tiên + 1 trích dẫn | Giả thuyết CP1: việc tìm hoạt động thay thế khi mưa khiến người lên lịch mất thêm thời gian đối chiếu đường đi và chi phí. Dự kiến phỏng vấn ít nhất 3 người ngoài nhóm đã lên lịch đi Hà Giang tự túc, đối chiếu với bài hỏi đáp du lịch công khai. Xem [giả thuyết](evidence/hypothesis.md). |
| 5 | **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả) | Khi người lên lịch cho nhóm bạn nhập số ngày, ngân sách mỗi người và thời điểm đi Hà Giang, AI chọn hoạt động thay thế cho một ngày có mưa từ các phương án đã qua kiểm tra về cung đường và chi phí để người đó nhận lịch từng ngày kèm tổng chi phí ước tính và lý do đổi lịch. |
| 6 | AI tự làm đến đâu + 1 dòng lý do: sai thì ai chịu gì | AI đề xuất, người lên lịch quyết định có dùng hay không vì cả nhóm chịu chi phí và thời gian nếu phương án sai. Python kiểm lại ngân sách và cung đường trước khi hiển thị. Thiếu dữ liệu thời tiết hoặc phương án phù hợp thì hệ thống nêu rõ giới hạn. |
| 7 | Phân công có tên | Đoàn Văn Tú (đội trưởng) – bộ xếp lịch, ngân sách và đổi lịch khi mưa. Nguyễn Đăng Doanh – Streamlit, Docker và triển khai EC2. Lê Nguyễn Hoàng Sơn – dữ liệu địa điểm, giá, cung đường và thời tiết. Nguyễn Thanh Tùng – hạ tầng AWS, tích hợp model, kiểm thử và demo. |
| — | *(CP2)* Đã đổi gì so với CP1 | |
