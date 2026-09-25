# Giao Thức Xây Dựng Bộ Dữ Liệu Thử Nghiệm DEV_PILOT (Pilot Dataset Protocol)

Tài liệu này quy định giao thức thiết kế, biên soạn thủ công và quản lý bộ dữ liệu thử nghiệm `DEV_PILOT` trong phân hệ DEV-02A của Math Knowledge Engine.

---

## 1. Nguyên Tắc Thiết Kế Bộ Dữ Liệu

1. **Biên soạn thủ công (Handcrafted Seeds)**: Không sinh tự động ngẫu nhiên hàng loạt. Mọi bài toán đều có chủ đích sư phạm và toán học rõ ràng.
2. **Bao phủ đầy đủ các lớp phương trình trong phạm vi nghiên cứu**: Tuyến tính (Linear), Bậc hai (Quadratic), Nhân tử chung (Factorable), Phân thức hữu tỉ (Rational), Trùng phương (Biquadratic).
3. **Cố tình đưa vào các ca bẫy và cận biên (Intentional Near-Misses)**:
   - Các phương trình xuất hiện nghiệm ngoại lai khi nhân chéo hoặc bỏ mẫu.
   - Các phương trình là đồng nhất thức trên miền xác định có lỗ thủng (Identity with excluded points).
   - Các phương trình có miền xác định rỗng ban đầu (Empty domain from outset).
   - Các phương trình vô nghiệm (No real roots).
   - Các phương trình có nghiệm bội (Double roots).
4. **Phân vùng dữ liệu nghiêm ngặt**:
   - Trong DEV-02A: 100% bản ghi thuộc phân vùng `DEV`.
   - Tuyệt đối không tạo hoặc sinh trước dữ liệu `VALIDATION` hoặc `TEST`.
   - Đảm bảo không xảy ra rò rỉ dữ liệu (Zero Data Leakage).

---

## 2. Danh Mục 15 Họ Bài Toán Hạt Nhân (15 Seed Families)

Bộ dữ liệu `DEV_PILOT` gồm 15 họ với tổng cộng 41 bài toán biến thể:

| STT | Family ID | Tên Họ Bài Toán | Lớp Phương Trình | Phương Pháp Chính | Split Group ID | Số Biến Thể |
|-----|-----------|-----------------|------------------|-------------------|----------------|-------------|
| 1 | `FAM_01_LINEAR_BASIC` | Tuyến tính cơ bản 1 nghiệm | `LINEAR` | `M1_LINEAR` | `SG_LINEAR_BASIC` | 3 |
| 2 | `FAM_02_LINEAR_FRACTIONAL_COEFF` | Tuyến tính hệ số phân số | `LINEAR` | `M1_LINEAR` | `SG_LINEAR_FRAC` | 3 |
| 3 | `FAM_03_LINEAR_RATIONAL_PARAM` | Tuyến tính hệ số hữu tỉ cụ thể | `LINEAR` | `M1_LINEAR` | `SG_LINEAR_RAT_PARAM` | 3 |
| 4 | `FAM_04_QUAD_TWO_ROOTS` | Bậc hai hai nghiệm thực phân biệt | `QUADRATIC` | `M2_QUADRATIC` | `SG_QUAD_RAT_TRANSFER` | 3 |
| 5 | `FAM_05_QUAD_DOUBLE_ROOT` | Bậc hai nghiệm kép | `QUADRATIC` | `M2_QUADRATIC` | `SG_QUAD_DOUBLE` | 3 |
| 6 | `FAM_06_QUAD_NO_REAL_ROOTS` | Bậc hai vô nghiệm thực | `QUADRATIC` | `M2_QUADRATIC` | `SG_QUAD_NO_REAL` | 3 |
| 7 | `FAM_07_FACTOR_COMMON_LINEAR` | Đưa về tích chứa nhân tử tuyến tính | `FACTORABLE` | `M3_FACTOR_COMMON` | `SG_FACTOR_COMMON` | 3 |
| 8 | `FAM_08_FACTOR_QUADRATIC_PRODUCT` | Tích hai đa thức bậc hai | `FACTORABLE` | `M3_FACTOR_COMMON` | `SG_FACTOR_QUAD` | 2 |
| 9 | `FAM_09_RAT_EXTRANEOUS_DENOM_ROOT` | Phân thức hữu tỉ có nghiệm triệt tiêu mẫu | `RATIONAL` | `M4_RATIONAL` | `SG_RAT_EXTRANEOUS` | 3 |
| 10 | `FAM_10_RAT_MULTIPLE_DENOMS` | Phân thức nhiều mẫu thức khác nhau | `RATIONAL` | `M4_RATIONAL` | `SG_RAT_MULTI_DENOM` | 3 |
| 11 | `FAM_11_RAT_EXTRANEOUS_TRANSFER` | Phân thức bẫy chuyển giao từ phương trình bậc hai | `RATIONAL` | `M4_RATIONAL` | `SG_QUAD_RAT_TRANSFER` | 3 |
| 12 | `FAM_12_RAT_DOMAIN_BOUNDARIES` | Phân thức biên miền: đồng nhất thức thủng vs miền rỗng | `RATIONAL` | `M4_RATIONAL` | `SG_RAT_DOMAIN_BOUND` | 3 |
| 13 | `FAM_13_BIQUAD_FOUR_ROOTS` | Trùng phương bốn nghiệm thực phân biệt | `BIQUADRATIC` | `M5_BIQUADRATIC` | `SG_BIQUAD_FOUR` | 3 |
| 14 | `FAM_14_BIQUAD_TWO_REAL_ROOTS` | Trùng phương hai nghiệm thực ($t_1>0, t_2<0$) | `BIQUADRATIC` | `M5_BIQUADRATIC` | `SG_BIQUAD_TWO` | 3 |
| 15 | `FAM_15_BIQUAD_NO_REAL_ROOTS` | Trùng phương vô nghiệm thực ($t_1<0, t_2<0$) | `BIQUADRATIC` | `M5_BIQUADRATIC` | `SG_BIQUAD_NO_REAL` | 3 |

---

## 3. Đặc Tả Chi Tiết Các Họ Cận Biên Quan Trọng

### 3.1 Họ `FAM_03_LINEAR_RATIONAL_PARAM` (Theo Điều Chỉnh 5 Của Người Điều Phối)
- Giới hạn nghiêm ngặt trong hệ số số học hữu tỉ cụ thể (ví dụ: `(3/4)*x - 5/6 = 0`, `(2/3)*x + 7/12 = 5/4`).
- Không đưa biến tham số mới (như `m, k, a, b`) vào hệ thống để không làm phình to phạm vi của bộ phân tích cú pháp DEV-01.

### 3.2 Họ `FAM_11_RAT_EXTRANEOUS_TRANSFER` (Theo Điều Chỉnh 1 Của Người Điều Phối)
- Là họ bài toán đích trong kịch bản chuyển giao nghiệm từ họ nguồn `FAM_04_QUAD_TWO_ROOTS`.
- Ví dụ: Bài toán nguồn `x^2 - 5*x + 6 = 0` ($x \in \{2, 3\}$). Bài toán đích `(x^2 - 5*x + 6)/(x - 2) = 0` chỉ nhận nghiệm hợp lệ $x=3$, điểm $x=2$ là nghiệm ngoại lai do $x-2 \neq 0$.
- Chia sẻ chung nhóm phụ thuộc: `split_group_id = "SG_QUAD_RAT_TRANSFER"`.

### 3.3 Họ `FAM_12_RAT_DOMAIN_BOUNDARIES` (Theo Điều Chỉnh 4 Của Người Điều Phối)
- Phân biệt minh thị giữa hai trạng thái cận biên toán học:
  1. **Đồng nhất thức trên miền xác định có lỗ thủng (Identity with excluded points)**:
     - Biến thể: `(x - 2)/(x - 2) = 1` hoặc `(x^2 - 1)/(x^2 - 1) = 1`.
     - Miền xác định: $\mathbb{R} \setminus \{2\}$ hoặc $\mathbb{R} \setminus \{-1, 1\}$.
     - Bản chất nghiệm: Mọi $x$ thuộc miền xác định đều thỏa mãn phương trình.
     - Thuộc tính schema: `is_identity_on_domain = True`, `is_empty_domain = False`.
  2. **Miền xác định rỗng ban đầu (Genuinely empty original domain)**:
     - Biến thể: `1/(x - 1) + 1/(1 - x) = 1/( (x - 2) - (x - 2) )` hoặc dạng có mẫu chứa hằng số 0 như `(x + 1)/0 = 0` hoặc ràng buộc mâu thuẫn triệt để.
     - Cụ thể trong pilot: `(x + 1)/((x - 1) - (x - 1)) = 0` (mẫu số rút gọn về 0 dẫn đến điều kiện $0 \neq 0$ không thể thỏa mãn với bất kỳ $x$ nào).
     - Thuộc tính schema: `is_identity_on_domain = False`, `is_empty_domain = True`.
     - Tập nghiệm: Rỗng ($\emptyset$).

---

## 4. Xác Thực Tính Nhất Quán & Toàn Vẹn

Bộ dữ liệu được kiểm tra tự động thông qua `KnowledgeBaseValidator`:
- Kiểm tra tính hợp lệ cú pháp JSONL.
- Xác thực Schema Pydantic cho từng bản ghi.
- Kiểm tra tính duy nhất của ID (không trùng lặp `problem_id`, `family_id`, `pair_id`).
- Kiểm tra toàn vẹn khóa ngoại (Referential Integrity): mọi `family_id`, `method_id`, `problem_id` tham chiếu đều phải tồn tại.
- Kiểm tra ràng buộc phân vùng (Split Group Integrity): các họ phụ thuộc và các cặp chuyển giao phải có chung `split_group_id`.
- Phát hiện trùng lặp biểu thức phương trình (Canonical Expression Duplication).
- Đối soát hàm băm SHA-256 trong `manifest.json`.
