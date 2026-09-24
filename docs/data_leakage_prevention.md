# Quy Trình Quản Lý Dữ Liệu & Chống Rò Rỉ Thông Tin (Data Leakage Prevention)

Tài liệu này quy định cấu trúc lưu trữ và nguyên tắc kiểm soát dữ liệu nghiên cứu nhằm đảm bảo tính tái lập và độ tin cậy khoa học của đề tài.

---

## 1. Nguyên Tắc Cốt Lõi Trong DEV-01

1. **Tuyệt đối không chứa nhãn chuẩn (Gold Labels) trong thành phần Inference**:
   - Thành phần suy luận và giải toán (`mke.parsing`, `mke.methods`, `mke.verification`) hoàn toàn không có quyền truy cập vào dữ liệu kiểm thử hoặc nhãn định sẵn.
   - Quá trình suy diễn hoàn toàn dựa trên cấu trúc toán học của phương trình đầu vào.
2. **Bộ Dữ Liệu Khảo Sát**:
   - Trong giai đoạn DEV-01, **chỉ sử dụng bộ Smoke Test tự biên soạn độc lập** (`data/smoke/smoke_fixtures.json`) gồm 8 trường hợp bắt buộc (T1 - T8) và các ca phát hiện rủi ro chuyển giao nghiệm.
   - Chưa phát hành bộ TEST chính thức.
   - Không tự động sinh 80 families rồi công bố kết quả benchmark khi chưa có kiểm định độc lập.
   - Không thực hiện hyperparameter tuning trên tập dữ liệu đánh giá.

---

## 2. Thiết Kế Phân Vùng Cho Các Giai Đoạn Tiếp Theo

Hệ thống thiết kế sẵn enum `Split`:
```python
class Split(str, Enum):
    DEV = "DEV"
    VALIDATION = "VALIDATION"
    TEST = "TEST"
```

- **DEV**: Sử dụng cho việc phát triển giải thuật, gỡ lỗi và kiểm thử chức năng ban đầu.
- **VALIDATION**: Sử dụng để thẩm định ngưỡng và so sánh sơ bộ giả thuyết H1.
- **TEST**: Bộ dữ liệu đóng băng, tuyệt đối không được sử dụng để tinh chỉnh logic hay quan sát trước khi chạy thực nghiệm cuối cùng.

---

## 3. Cấu Trúc Bản Ghi Bài Toán Nghiên Cứu (`ProblemRecord`)

Mỗi bài toán nghiên cứu được mô hình hóa theo định dạng schema JSON có kiểm tra kiểu dữ liệu:
- `family_id`: Định danh họ bài toán (dùng để kiểm tra chuyển giao phương pháp).
- `problem_id`: Mã bài toán duy nhất.
- `split`: Phân vùng dữ liệu (`DEV`, `VALIDATION`, `TEST`).
- `raw_input`: Chuỗi phương trình nguyên bản.
- `raw_ast`: Cây cú pháp nguyên bản chưa rút gọn.
- `domain_conditions`: Danh sách điều kiện miền xác định.
- `normalization_trace`: Nhật ký từng bước biến đổi đại số.
- `method_id` & `method_version`: Định danh phương pháp và phiên bản áp dụng.
- `obligations`: Danh sách nghĩa vụ chứng minh và trạng thái kiểm chứng thực tế.
- `transfer_validity`: Nhãn đánh giá tính an toàn khi chuyển giao nghiệm.
- `is_verified_method` & `is_verified_solution`: Tách biệt việc áp dụng phương pháp hợp lệ và chứng minh nghiệm đầy đủ.
- `reviewer_log`: Nhật ký kiểm toán viên nghiên cứu.
- `provenance` & `license_status`: Nguồn gốc xuất xứ và bản quyền của bài toán.
