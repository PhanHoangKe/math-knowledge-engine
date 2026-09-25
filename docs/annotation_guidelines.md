# Hướng Dẫn Gán Nhãn & Thẩm Định Tri Thức Toán Học (Annotation Guidelines)

Tài liệu này quy định quy trình gán nhãn, thẩm định phương pháp và duy trì tính liêm chính khoa học cho Math Knowledge Engine (MKE) theo phân hệ DEV-02A.

---

## 1. Nguyên Tắc Liêm Chính Khoa Học (Scientific Integrity)

1. **Không Tự Đóng Dấu Chân Lý Tuyệt Đối**:
   - Tuyệt đối không sử dụng kết quả dự đoán của DEV-01 làm nhãn chuẩn (gold labels) để tự đánh giá lại chính DEV-01 (tránh vòng luẩn quẩn đánh giá - circular evaluation).
   - Mọi bản ghi gán nhãn chưa qua quy trình thẩm định ngang hàng (peer-review) độc lập bởi chuyên gia toán học bắt buộc phải đặt `review_status = ReviewStatus.PROVISIONAL`.
2. **Bảo Tồn Bất Đồng (Preserve Discrepancies)**:
   - Khi bộ kiểm chứng DEV-01 đưa ra kết quả khác với nhãn gán ban đầu, hệ thống **không được phép tự động ghi đè hoặc âm thầm sửa đổi** nhãn gán.
   - Bất đồng phải được ghi nhận công khai, chi tiết trong báo cáo `DEV02A_DISCREPANCIES.json` để phục vụ phân tích khoa học và đối thoại phản biện.
3. **Phân Tách Bạch Minh Thị Các Khái Niệm**:
   - Mẫu phương pháp trừu tượng (`MethodTemplate`).
   - Thể hiện cụ thể trên bài toán (`MethodInstance`).
   - Tính thừa nhận của phương pháp (`MethodAdmissibility`).
   - Tính an toàn của việc chuyển giao nghiệm (`TransferCategory`).
   - Tính đầy đủ toán học của tập nghiệm (`CompletenessProofStatus`).

---

## 2. Quy Trình Gán Nhãn Bản Ghi `MethodAnnotation`

Mỗi bản ghi gán nhãn phải tuân thủ nghiêm ngặt cấu trúc:
- `annotation_id`: Mã định danh duy nhất có quy ước `ANN_<problem_id>_<method_id>`.
- `problem_id`: Mã bài toán được gán nhãn.
- `method_id`: Mã phương pháp giải.
- `method_version`: Phiên bản phương pháp (chuẩn `1.0.0`).
- `method_instance_id`: Mã thể hiện phương pháp tương ứng (`INST_<problem_id>_<method_id>`).
- `admissibility`: Đánh giá tính thừa nhận của phương pháp.
  - `APPLICABLE`: Phương pháp áp dụng được trực tiếp và an toàn.
  - `APPLICABLE_WITH_OBLIGATIONS`: Phương pháp áp dụng được nhưng phát sinh nghĩa vụ chứng minh (ví dụ: cần kiểm tra điều kiện mẫu số khác 0 đối với M4).
  - `REFUTED`: Phương pháp bị bác bỏ dứt khoát do vi phạm cấu trúc hoặc tiền điều kiện.
  - `UNKNOWN`: Trạng thái chưa đủ căn cứ xác minh độc lập.
- `completeness`:
  - `SOUND_AND_COMPLETE`: Tìm đủ toàn bộ nghiệm và không chứa nghiệm ngoại lai.
  - `SOUND_INCOMPLETE`: Nghiệm tìm được là đúng nhưng chưa chứng minh vét cạn hết nghiệm.
  - `UNSOUND`: Chứa nghiệm ngoại lai hoặc vi phạm miền xác định.
  - `UNKNOWN`: Chưa chứng minh được.
- `review_status`:
  - `PROVISIONAL`: Gán nhãn sơ bộ trong quá trình phát triển (mặc định cho toàn bộ DEV_PILOT).
  - `PEER_REVIEWED`: Đã qua kiểm tra độc lập bởi ít nhất một nghiên cứu viên thứ hai.
  - `EXPERT_VERIFIED`: Đã được thẩm định chính thức bởi hội đồng chuyên môn.
  - `REJECTED`: Nhãn gán bị bác bỏ do sai sót toán học.
- `annotator`: Tên/mã người tạo nhãn.
- `verification_notes`: Căn cứ toán học chi tiết lý giải vì sao phương pháp được thừa nhận hay bác bỏ.

---

## 3. Quy Tắc Gán Nhãn Cặp Chuyển Giao `TransferPairRecord`

1. **Mục đích**: Đánh giá giả thuyết H1 khi một phương pháp hoặc nghiệm của phương trình nguồn được chuyển giao sang phương trình đích.
2. **Các loại hình chuyển giao (`transfer_category`)**:
   - `DIRECT_TRANSFER`: Chuyển giao trực tiếp, nghiệm và phương pháp được bảo toàn đầy đủ.
   - `DOMAIN_BLOCKED`: Chuyển giao bị chặn bởi miền xác định của bài toán đích (nghiệm nguồn nằm ngoài miền xác định đích).
   - `UNSAFE_COPY`: Chép lời giải từ nguồn sang đích một cách ngây thơ dẫn đến sai lệch toán học (ví dụ: tạo nghiệm ngoại lai do bài toán đích có mẫu số triệt tiêu).
   - `REPRESENTATION_SHIFT`: Phương trình cần chuyển đổi biểu diễn trước khi tái sử dụng phương pháp.
3. **Trường hợp bắt buộc FAM_04 $\rightarrow$ FAM_11**:
   - Nguồn: `PROB_FAM04_V01` ($x^2 - 5x + 6 = 0 \Rightarrow x \in \{2, 3\}$).
   - Đích: `PROB_FAM11_V01` ($\frac{x^2 - 5x + 6}{x - 2} = 0$).
   - Phân loại: `UNSAFE_COPY`.
   - `is_safe`: `False`.
   - `failure_mode`: "Direct transfer of roots {2, 3} without verifying target denominator constraint x - 2 != 0 admits extraneous root x = 2."
   - `proof_obligations_needed`: `["OB_ROOT_IN_ORIGINAL_DOMAIN", "OB_DENOM_NONZERO"]`.
   - Bắt buộc kiểm tra ràng buộc `split_group_id`: Cả hai bài toán phải có cùng `split_group_id = "SG_QUAD_RAT_TRANSFER"`.

---

## 4. Danh Sách Kiểm Tra Khi Gán Nhãn (Reviewer Checklist)

Trước khi chuyển trạng thái nhãn gán, người thẩm định phải kiểm tra:
- [ ] Phương trình có miền xác định rỗng hay không?
- [ ] Phương trình có phải là đồng nhất thức trên miền xác định có lỗ thủng hay không?
- [ ] Phép biến đổi đại số có phải là phép biến đổi tương đương ($\Leftrightarrow$) hay chỉ là phép biến đổi hệ quả ($\Rightarrow$)?
- [ ] Nếu là biến đổi hệ quả, nghĩa vụ kiểm tra lại nghiệm trên miền xác định ban đầu đã được thiết lập chưa?
- [ ] Các điểm nghiệm có phải là số thực chính xác (Exact Symbolic) hay là xấp xỉ dấu phẩy động?
- [ ] Bản ghi có mã thể hiện phương pháp `method_instance_id` hợp lệ và tồn tại trong cơ sở dữ liệu không?
