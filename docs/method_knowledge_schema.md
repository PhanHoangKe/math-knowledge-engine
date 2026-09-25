# Đặc Tả Kiến Trúc Biểu Diễn Tri Thức Phương Pháp (Method Knowledge Schema)

Tài liệu này đặc tả chi tiết kiến trúc biểu diễn tri thức phương pháp giải phương trình đại số (M1 – M5), các thể hiện phương pháp, các cặp chuyển giao và quy chuẩn lưu trữ trong Math Knowledge Engine (MKE) theo phân hệ DEV-02A.

---

## 1. Mục Tiêu Thiết Kế

1. **Tách biệt biểu diễn trừu tượng và thực thi**: Tách biệt rõ ràng giữa mẫu phương pháp trừu tượng (`MethodTemplate`), thể hiện cụ thể trên bài toán (`MethodInstance`), và kết quả chuyển giao giải pháp (`TransferPairRecord`).
2. **Kiểm tra chặt chẽ bằng Pydantic**: Mọi thực thể dữ liệu được định nghĩa với kiểu dữ liệu rõ ràng, ràng buộc giá trị hợp lệ, kiểm tra khóa ngoại và quan hệ phụ thuộc.
3. **Lưu trữ chuẩn tắc (Canonical JSONL)**: Dữ liệu nguồn được lưu trữ dưới dạng JSONL chuẩn hóa (UTF-8, sort_keys=True, compact separators, LF line-endings) kèm hàm băm SHA-256 nội dung độc lập với thời gian hoặc hệ điều hành.
4. **Chỉ mục SQLite xác định (Deterministic SQLite Index)**: Cung cấp khả năng truy vấn quan hệ nhanh chóng, có thể tái tạo 100% từ tệp JSONL mà không làm thay đổi hay phụ thuộc vào dữ liệu nguồn.

---

## 2. Các Thực Thể Tri Thức (Core Knowledge Entities)

### 2.1 Phương Pháp Trừu Tượng (`MethodTemplate`)
Đại diện cho một phương pháp toán học được phân loại trong hệ thống:
- `method_id`: Mã phương pháp duy nhất (`M1_LINEAR`, `M2_QUADRATIC`, `M3_FACTOR_COMMON`, `M4_RATIONAL`, `M5_BIQUADRATIC`).
- `name`: Tên phương pháp bằng tiếng Việt / tiếng Anh.
- `version`: Phiên bản phương pháp (chuẩn `1.0.0`).
- `equation_class`: Lớp phương trình áp dụng (`LINEAR`, `QUADRATIC`, `FACTORABLE`, `RATIONAL`, `BIQUADRATIC`).
- `preconditions`: Danh sách tiền điều kiện cấu trúc dạng chuỗi hình thức.
- `guards`: Danh sách các phép kiểm tra bảo vệ toán học (guard name, description, expression rule).
- `proof_obligations`: Danh sách nghĩa vụ chứng minh phát sinh (obligation ID, description, required status).
- `transformation_steps`: Các bước biến đổi đại số tương ứng.
- `failure_modes`: Các chế độ thất bại đã biết (ví dụ: chia cho 0, nghiệm ngoại lai do nhân tử chung chứa ẩn).
- `target_equation_classes`: Các lớp phương trình kết quả sau khi quy đổi (ví dụ: M4 quy đổi về LINEAR hoặc QUADRATIC).
- `content_hash`: Hàm băm SHA-256 nội dung của phương pháp.

### 2.2 Thể Hiện Phương Pháp (`MethodInstance`)
Đại diện cho việc áp dụng một phương pháp cụ thể vào một bài toán xác định:
- `instance_id`: Mã thể hiện duy nhất (`INST_<problem_id>_<method_id>`).
- `problem_id`: Khóa ngoại tham chiếu tới `ProblemRecord`.
- `method_id`: Khóa ngoại tham chiếu tới `MethodTemplate`.
- `method_version`: Phiên bản của phương pháp tại thời điểm áp dụng.
- `admissibility`: Tính thừa nhận được (`APPLICABLE`, `APPLICABLE_WITH_OBLIGATIONS`, `REFUTED`, `UNKNOWN`).
- `guard_results`: Kết quả chi tiết của từng guard (tên guard, đạt/không đạt, bằng chứng).
- `obligations_raised`: Danh sách nghĩa vụ chứng minh được sinh ra.
- `substitution_map`: Bản đồ tham số đại số cụ thể (ví dụ: `{"a": "1", "b": "-5", "c": "6"}`).

### 2.3 Họ Bài Toán (`FamilyRecord`)
Nhóm các bài toán có chung cấu trúc toán học hoặc nguồn gốc biến đổi:
- `family_id`: Mã họ duy nhất (ví dụ: `FAM_01_LINEAR_BASIC`, `FAM_11_RAT_EXTRANEOUS_TRANSFER`).
- `name`: Tên họ bài toán.
- `equation_class`: Phân loại cấu trúc chính.
- `split_group_id`: Định danh nhóm phân chia dữ liệu chống rò rỉ (Data Leakage Guard).
- `dependent_family_ids`: Danh sách mã họ phụ thuộc (bắt buộc cùng `split_group_id`).
- `description`: Mô tả cấu trúc toán học chung.
- `primary_method_id`: Phương pháp chính áp dụng cho họ này.
- `variant_count`: Số lượng bài toán biến thể trong họ.
- `tags`: Nhãn phân loại phục vụ tìm kiếm.

### 2.4 Bài Toán Nghiên Cứu (`ProblemRecord`)
Mỗi bài toán đại số cụ thể trong tập dữ liệu:
- `problem_id`: Mã bài toán duy nhất (ví dụ: `PROB_FAM01_V01`).
- `family_id`: Khóa ngoại tham chiếu `FamilyRecord`.
- `equation_text`: Chuỗi biểu diễn phương trình đại số đầu vào.
- `split`: Phân vùng dữ liệu (`DEV`, `VALIDATION`, `TEST`). Trong DEV-02A: 100% `DEV`.
- `variable`: Biến số ẩn (mặc định `"x"`).
- `canonical_equation`: Biểu diễn chuẩn hóa toán học.
- `original_domain_latex`: Miền xác định ban đầu dưới dạng chuỗi toán học.
- `excluded_values`: Tập các điểm bị loại trừ khỏi miền xác định.
- `intended_method_ids`: Danh sách các phương pháp dự kiến áp dụng.
- `ground_truth_roots`: Tập nghiệm thực tế đã được xác thực độc lập.
- `is_identity_on_domain`: Cờ đánh dấu phương trình là đồng nhất thức trên miền xác định.
- `is_empty_domain`: Cờ đánh dấu phương trình có miền xác định rỗng ban đầu.
- `source`: Nguồn gốc xuất xứ (ví dụ: `HANDCRAFTED_PILOT`).
- `notes`: Ghi chú sư phạm / toán học.

### 2.5 Nhãn Gán Phương Pháp (`MethodAnnotation`)
Bản ghi liên kết giữa bài toán và phương pháp:
- `annotation_id`: Mã bản ghi chú giải (`ANN_<problem_id>_<method_id>`).
- `problem_id`: Khóa ngoại bài toán.
- `method_id`: Khóa ngoại phương pháp.
- `method_version`: Phiên bản phương pháp.
- `method_instance_id`: Khóa ngoại thể hiện phương pháp cụ thể.
- `admissibility`: Đánh giá tính thừa nhận của phương pháp.
- `completeness`: Đánh giá tính đầy đủ của nghiệm (`SOUND_AND_COMPLETE`, `SOUND_INCOMPLETE`, `UNSOUND`, `UNKNOWN`).
- `review_status`: Trạng thái thẩm định (`PROVISIONAL`, `PEER_REVIEWED`, `EXPERT_VERIFIED`, `REJECTED`). Mọi annotation chưa được chuyên gia độc lập ký duyệt bắt buộc để `PROVISIONAL`.
- `annotator`: Tên/mã người tạo chú giải.
- `verification_notes`: Ghi chú chi tiết về căn cứ toán học.

### 2.6 Cặp Chuyển Giao Phương Pháp (`TransferPairRecord`)
Bản ghi kiểm thử chuyển giao giải pháp giữa bài toán nguồn và bài toán đích:
- `pair_id`: Mã định danh cặp chuyển giao.
- `source_problem_id`: Khóa ngoại bài toán nguồn.
- `target_problem_id`: Khóa ngoại bài toán đích.
- `source_method_id`: Phương pháp được sử dụng tại nguồn.
- `transfer_category`: Phân loại chuyển giao (`DIRECT_TRANSFER`, `DOMAIN_BLOCKED`, `UNSAFE_COPY`, `REPRESENTATION_SHIFT`).
- `is_safe`: Cờ xác nhận việc chuyển giao nghiệm có bảo toàn tính đúng đắn toán học hay không.
- `failure_mode`: Mô tả cơ chế thất bại nếu chuyển giao không an toàn (ví dụ: tạo nghiệm ngoại lai do bỏ qua mẫu số).
- `proof_obligations_needed`: Danh sách nghĩa vụ chứng minh bắt buộc phải thiết lập để việc chuyển giao an toàn.
- `split_group_id`: Bắt buộc trùng khớp với `split_group_id` của cả hai họ bài toán liên quan.

---

## 3. Kiến Trúc Lưu Trữ & Chỉ Mục

```
data/
├── knowledge/
│   ├── methods.jsonl       # 5 Phương pháp chuẩn hóa (M1 - M5)
│   └── manifest.json       # Manifest và SHA-256 của kho tri thức
└── dev_pilot/
    ├── families.jsonl      # 15 Họ bài toán pilot
    ├── problems.jsonl      # 41 Bài toán biến thể (100% DEV)
    ├── annotations.jsonl   # 43 Bản ghi gán nhãn phương pháp
    ├── transfer_pairs.jsonl# 4 Cặp chuyển giao kiểm thử
    └── manifest.json       # Manifest chi tiết kèm SHA-256 từng tệp
```

### Quy Tắc Serialization Chuẩn Tắc
Để đảm bảo tính tái lập (Reproducibility) giữa các hệ điều hành và môi trường chạy:
1. `sort_keys=True`: Thứ tự các trường khóa luôn ổn định theo bảng chữ cái.
2. `separators=(',', ':')`: Loại bỏ khoảng trắng dư thừa, định dạng compact.
3. `ensure_ascii=False`: Hỗ trợ ký tự toán học và tiếng Việt UTF-8 chuẩn.
4. `\n` LF Line-endings: Chuẩn hóa ngắt dòng Unix LF (loại trừ `\r\n` của Windows khi tính hash).
5. Hash nội dung không chứa trường thời gian (`created_at`, `timestamp`) hoặc trạng thái chỉ mục SQLite.
