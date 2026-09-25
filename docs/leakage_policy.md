# Chính Sách Phòng Chống Rò Rỉ Dữ Liệu Nghiên Cứu (Data Leakage Policy)

Tài liệu này quy định các chính sách và cơ chế kỹ thuật nhằm ngăn chặn triệt để hiện tượng rò rỉ dữ liệu (Data Leakage) giữa các phân vùng nghiên cứu trong Math Knowledge Engine (MKE).

---

## 1. Bản Chất Rủi Ro Rò Rỉ Trong Bài Toán Truy Xuất & Chuyển Giao Phương Pháp

Trong nghiên cứu kiểm tra giả thuyết H1 (truy xuất và tái sử dụng phương pháp giải phương trình):
- Nếu bài toán nguồn (source problem) nằm trong tập huấn luyện (`DEV`) và bài toán đích (target problem) nằm trong tập đánh giá (`TEST`), nhưng cả hai lại liên quan trực tiếp qua phép chuyển giao giải pháp (solution transfer), mô hình truy xuất có thể "học vẹt" hoặc bị rò rỉ cấu trúc nghiệm.
- Hiện tượng này làm sai lệch nghiêm trọng kết quả thực nghiệm, dẫn đến những tuyên bố sai về tính khái quát hóa và độ tin cậy khoa học.

---

## 2. Cơ Chế Nhóm Phân Vùng Chống Rò Rỉ (`split_group_id`)

Nhằm khắc phục triệt để nguy cơ rò rỉ dữ liệu cấp độ họ bài toán:
1. **Trường `split_group_id` bắt buộc**:
   - Mọi `FamilyRecord` đều phải khai báo `split_group_id`.
   - Các họ bài toán có liên kết phụ thuộc biến đổi, quan hệ tương đồng cao hoặc có bài toán tham gia vào cùng một cặp chuyển giao (`TransferPairRecord`) **bắt buộc phải có cùng `split_group_id`**.
2. **Quan hệ phụ thuộc giữa các họ (`dependent_family_ids`)**:
   - Nếu Family B sử dụng bài toán từ Family A làm nguồn chuyển giao hoặc kế thừa cấu trúc biến đổi, Family B phải khai báo `dependent_family_ids = ["FAM_A"]`.
   - Ràng buộc toàn vẹn: Tất cả các họ trong danh sách phụ thuộc phải có cùng `split_group_id`.
3. **Trường Hợp Bắt Buộc Trong DEV-02A**:
   - `FAM_04_QUAD_TWO_ROOTS` (Phương trình bậc hai hai nghiệm phân biệt) và `FAM_11_RAT_EXTRANEOUS_TRANSFER` (Phương trình phân thức bẫy chuyển giao nghiệm ngoại lai) có quan hệ phụ thuộc nhân - quả chuyển giao.
   - Do đó, cả hai họ này bắt buộc phải thuộc cùng một nhóm:
     ```json
     "split_group_id": "SG_QUAD_RAT_TRANSFER"
     ```
   - `FAM_11_RAT_EXTRANEOUS_TRANSFER.dependent_family_ids = ["FAM_04_QUAD_TWO_ROOTS"]`.

---

## 3. Quy Tắc Phân Vùng Trong Tương Lai (Future Split Policy)

Khi hệ thống mở rộng sang giai đoạn chia tập dữ liệu huấn luyện, thẩm định và kiểm thử:
1. **Nguyên tắc không chia cắt nhóm phụ thuộc (Indivisible Split Groups)**:
   - Toàn bộ các họ bài toán có cùng `split_group_id` bắt buộc phải nằm trong **CÙNG MỘT PHÂN VÙNG** (`DEV`, `VALIDATION`, hoặc `TEST`).
   - Tuyệt đối nghiêm cấm việc đặt Family nguồn ở tập `DEV` và Family đích ở tập `TEST` khi chúng thuộc cùng `split_group_id`.
2. **Trạng thái nghiêm ngặt trong DEV-02A**:
   - Trong giai đoạn DEV-02A hiện tại, **100% dữ liệu bài toán thuộc phân vùng `DEV` (`Split.DEV`)**.
   - Tuyệt đối không tạo, không phát sinh trước dữ liệu thuộc `VALIDATION` hoặc `TEST`.
   - Bất kỳ bản ghi nào có `split != Split.DEV` sẽ bị `KnowledgeBaseValidator` đánh dấu là lỗi nghiêm trọng (Violation Error).

---

## 4. Phát Hiện Trùng Lặp Biểu Thức Phương Trình (Duplicate Detection)

1. **Chuẩn hóa biểu thức trước khi kiểm tra**:
   - Mọi phương trình đều được chuyển về dạng chuẩn tắc tối giản qua `normalize_equation`.
   - Hệ thống kiểm tra xem hai bài toán khác nhau có cùng biểu thức chuẩn tắc hay không.
2. **Chính sách đối với biểu thức trùng lặp**:
   - Trong cùng một tập dữ liệu, hai bài toán có cùng biểu thức chuẩn tắc nhưng khác `family_id` hoặc khác `split` bị coi là dấu hiệu rò rỉ dữ liệu hoặc dư thừa không cần thiết.
   - `KnowledgeBaseValidator` sẽ quét và cảnh báo tất cả các cặp bài toán có biểu thức toán học tương đương.
