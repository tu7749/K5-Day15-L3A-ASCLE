# Canvas — ASCLE · Track C (Du lịch)

> Điền ở guide bước 1.4. CP1 17:00 Thứ Sáu 27/11: nộp bản đầu, đủ 7 dòng (dòng 4 được ghi giả thuyết + nguồn sẽ kiểm).
> CP2 19:30 Thứ Sáu 27/11: cập nhật (số bằng chứng đầu, lát cắt đã chốt) và điền dòng "Đã đổi gì so với CP1".
> Track F: chép thêm thẻ đề của nhóm (khung trong file track F) xuống dưới bảng này.

| # | Dòng | Nhóm điền |
|---|---|---|
| 1 | Track + lát cắt dự kiến | Track C – Du lịch. Lịch mẫu 2–5 ngày tại một trong hai điểm đến Hà Giang và Đà Nẵng, kèm đề xuất thay một hoạt động ngày mưa khi có căn cứ. |
| 2 | Người dùng chính (một vai cụ thể — không phải "học viên nói chung") | Người đứng ra lên lịch chuyến đi tự túc cho nhóm bạn ở Hà Giang hoặc Đà Nẵng. |
| 3 | Pain một câu: ai — đang làm gì — vướng đâu — hậu quả | Người lên lịch chuyến đi tự túc cho nhóm bạn ở Hà Giang hoặc Đà Nẵng phải đối chiếu chi phí, cung đường và thời tiết từ nhiều nguồn nên tốn thời gian xếp lại lịch và tính lại tiền khi hoạt động ngoài trời gặp mưa. |
| 4 | Bằng chứng đầu — CP1: giả thuyết + nguồn sẽ kiểm · CP2: số đầu tiên + 1 trích dẫn | Bằng chứng đầu CP2: 6/8 bài hỏi đáp trong mẫu thăm dò cân nhắc giữ, hoãn hoặc đổi hoạt động vì mưa. “What indoor activities do you recommend when it’s rainy?” Xem [nguồn R05 và giới hạn của mẫu](evidence/data-mining.md). Chưa đo thời gian và chi phí phát sinh. |
| 5 | **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả) | Khi người lên lịch cho nhóm bạn chọn Hà Giang hoặc Đà Nẵng và nhập số ngày, ngân sách mỗi người cùng thời điểm đi, AI chọn một hoạt động thay thế từ các phương án đủ căn cứ cho một ngày mưa để người đó nhận lịch mẫu kèm tổng chi phí ước tính và lý do đổi. |
| 6 | AI tự làm đến đâu + 1 dòng lý do: sai thì ai chịu gì | AI đề xuất, người lên lịch quyết định có dùng hay không vì cả nhóm chịu chi phí và thời gian nếu phương án sai. Python kiểm lại ngân sách và cung đường trước khi hiển thị. Thiếu dữ liệu thời tiết hoặc phương án phù hợp thì hệ thống nêu rõ giới hạn. |
| 7 | Phân công có tên | Đoàn Văn Tú (đội trưởng) – bộ xếp lịch, ngân sách, đổi lịch và tích hợp model. Nguyễn Đăng Doanh – giao diện, Docker và AWS. Lê Nguyễn Hoàng Sơn – dữ liệu và thời tiết. Nguyễn Thanh Tùng – kiểm thử và demo. |
| — | *(CP2)* Đã đổi gì so với CP1 | Đã đọc tập bài hỏi đáp ban đầu và nối CSV của hai điểm đến. Giới hạn đề xuất đổi ở một ngày và chỉ chọn điểm trong nhà có vé, tuyến và phần ngân sách phù hợp. Thời tiết dùng kịch bản có nhãn, Hà Giang để trống ngày mưa khi thiếu phương án. Bản Streamlit thử nghiệm đọc thêm bảng lưu trú và dùng Python xếp lịch; hồ sơ đánh giá CP2 vẫn chạy qua CLI. |
