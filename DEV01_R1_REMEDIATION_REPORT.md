# BÁO CÁO KHẮC PHỤC KIỂM TOÁN ĐỘC LẬP DEV-01-R1
## (Independent Audit Remediation Report)

**Dự án:** Math Knowledge Engine (MKE)  
**Nhiệm vụ:** DEV-01-R1 — Independent Audit Remediation  
**Giai đoạn:** DEV-01 (Nền tảng kiểm chứng toán học & suy luận giải tích)  
**Ngày thực hiện:** 24/09/2026  
**Nhánh Git:** `dev01-r1-audit-fixes`  
**Kỹ sư thực hiện:** Senior Mathematical Software Engineer, Python Security Engineer & Research Reproducibility Engineer  
**Trạng thái kiểm thử:** **97/97 tests passed** (82 DEV-01 baseline tests + 15 R1–R6 regression tests) | **8/8 smoke cases passed** (100%)  

---

## 1. TỔNG QUAN VÀ CAM KẾT PHẠM VI NGHIÊN CỨU

Theo kết quả kiểm toán độc lập của Người điều phối dự án, giai đoạn DEV-01 đã hoàn thành kiến trúc nền tảng nhưng còn tồn tại 6 vấn đề kỹ thuật toán học và an toàn dữ liệu cần khắc phục trước khi nghiệm thu độc lập.

Báo cáo này tài liệu hóa đầy đủ quá trình khắc phục triệt để 6 vấn đề trên nhánh `dev01-r1-audit-fixes`, bảo toàn 100% chức năng và bài kiểm thử đã có (82/82), bổ sung bộ kiểm thử hồi quy độc lập R1–R6 (15 bài kiểm thử mới, nâng tổng số lên 97 bài kiểm thử đạt).

**Cam kết tuân thủ ranh giới nghiên cứu:**
- Tuyệt đối **KHÔNG** chuyển sang DEV-02.
- Tuyệt đối **KHÔNG** triển khai RAG, LLM integration, giao diện đồ họa (GUI/Web), hay vector database.
- Thực thi CPU-first, môi trường cục bộ Windows 64-bit hoàn toàn không phụ thuộc API bên ngoài.
- Dữ liệu và kết quả hoàn toàn trung thực, có thể tái lập thực nghiệm độc lập.

---

## 2. KẾT QUẢ KHẮC PHỤC CHI TIẾT THEO TỪNG VẤN ĐỀ (R1 - R6)

### R1. Thứ tự ưu tiên toán tử lũy thừa và dấu trừ đơn thức (Operator Precedence & Round-trip AST)

- **Hiện tượng lỗi gốc:**
  Trong `Parser._parse_power()`, cơ số của phép lũy thừa `^` được phân tích bằng `_parse_unary()`. Khi phân tích `-x^2`, bộ phân tích gán dấu trừ vào biến $x$ trước thành `(-x)`, sau đó mới nâng lên lũy thừa 2 thành `(-x)^2 = x^2`. Điều này khiến:
  - `-x^2 + 4 = 0` bị chuyển thành `x^2 + 4 = 0` (vô nghiệm thực, sai lệch toán học).
  - `-2^2` bị tính thành `(-2)^2 = 4` thay vì $-4$.
- **Giải pháp khắc phục:**
  1. Cấu trúc lại ngữ pháp phân tích đệ quy đi xuống:
     - `_parse_term` $\to$ gọi `_parse_unary` (ưu tiên toán tử nhân/chia).
     - `_parse_unary` $\to$ nhận diện tiền tố `+` hoặc `-`, sau đó gọi đệ quy `_parse_unary` hoặc chuyển tiếp xuống `_parse_power`.
     - `_parse_power` $\to$ gọi `_parse_primary` làm cơ số, rồi nhận diện `^` và số mũ.
     - Quy tắc: Phép lũy thừa `^` liên kết chặt hơn dấu trừ tiền tố `-`.
  2. Nâng cấp phương thức `to_math_string()` trong `ast_nodes.py`:
     - `BinaryOpNode.to_math_string()` kiểm tra nếu toán hạng bên trái là `UnaryOpNode` và toán tử là `^`, tự động bao đóng ngoặc đơn: `(-x) ^ 2`.
     - Đảm bảo tính nhất quán Round-trip: `AST -> to_math_string() -> Parser -> AST` hoàn toàn đồng nhất.
- **Minh chứng kiểm thử:**
  - `test_r1_operator_precedence_negative_power`: Giải `-x^2 + 4 = 0` trả về tập nghiệm $\{-2, 2\}$.
  - `test_r1_operator_precedence_parenthesized_vs_unparenthesized`: `-x^2` tạo AST đỉnh `UnaryOpNode("-", BinaryOpNode("^", x, 2))`, còn `(-x)^2` tạo đỉnh `BinaryOpNode("^", UnaryOpNode("-", x), 2)`.
  - `test_r1_negative_number_power`: Chuẩn hóa `-2^2 = x` trả về nghiệm $x = -4$; `(-2)^2 = x` trả về $x = 4$.
  - `test_r1_roundtrip_ast_math_string`: 7 biểu thức kiểm thử round-trip đạt 100%.

---

### R2. Số học miền xác định chính xác (Domain Exact Arithmetic & Float Epsilon Conflation)

- **Hiện tượng lỗi gốc:**
  Trong `OriginalDomain.contains(x_val)`, việc so sánh giá trị loại trừ sử dụng phép tính xấp xỉ dấu phẩy động: `abs(float(sym_val) - float(sym_excl)) < 1e-12`. Việc này gây ra lỗi nghiêm trọng: hai nghiệm đại số thực phân biệt nhưng cách nhau $< 10^{-12}$ sẽ bị gộp làm một, dẫn đến loại bỏ nhầm nghiệm hợp lệ.
- **Giải pháp khắc phục:**
  1. Loại bỏ hoàn toàn ngưỡng sai số `1e-12`.
  2. Triển khai so sánh số học chính xác hai lớp:
     - **Lớp 1 (Phân số hữu tỉ / Số nguyên):** So sánh giá trị chính xác qua `Fraction` hoặc `sympy.Rational` (`sym_val == sym_excl`).
     - **Lớp 2 (Số vô tỉ / Số đại số tổng quát):** So sánh hiệu đại số chính xác qua `diff = sympy.simplify(sym_val - sym_excl)`; chỉ kết luận trùng khi `diff == 0` hoặc `diff.is_zero is True`.
- **Minh chứng kiểm thử:**
  - `test_r2_exact_domain_close_roots_not_conflated`: Điểm loại trừ $x = 1/10^{13}$ ($10^{-13} < 10^{-12}$). Điểm $x = 0$ được xác nhận nằm trong miền (`contains(0) == True`), không bị conflate nhầm.
  - `test_r2_exact_symbolic_algebraic_comparison`: Điểm đại số $\sqrt{2}$ và $\frac{2}{\sqrt{2}}$ được nhận diện là cùng một giá trị đại số chính xác; giá trị xấp xỉ số học $1.41421356237$ không bị loại trừ sai.

---

### R3. Xử lý mẫu số đồng nhất bằng 0 & Miền rỗng (Identically Zero Denominator & Empty Domain)

- **Hiện tượng lỗi gốc:**
  - Khi phương trình chứa phép chia cho 0 hằng số (ví dụ: `x / 0 = 0`) hoặc đa thức mẫu số triệt tiêu đồng nhất (ví dụ: `1 / (x - x) = 0`), bộ trích xuất miền trước đây đưa `{sympy.S.Reals}` vào `excluded_values`. Khi gọi `contains()`, do `float(S.Reals)` ném ngoại lệ nên phương thức mặc định trả về `True`, khiến phương trình vô nghĩa lại được coi là xác định trên toàn bộ $\mathbb{R}$.
- **Giải pháp khắc phục:**
  1. Thêm cờ trạng thái tường minh vào `DomainCondition` và `OriginalDomain`:
     - `is_empty_domain: bool = False`
     - `is_undetermined: bool = False`
  2. Khi mẫu số triệt tiêu đồng nhất trên $\mathbb{R}$:
     - Đặt `is_empty_domain = True`, `format_domain() = "\\emptyset"`.
     - Không bao giờ lưu trữ `sympy.S.Reals` vào tập điểm rời rạc `excluded_values`.
     - `contains(x_val)` lập tức trả về `False` với mọi $x \in \mathbb{R}$.
  3. `VerificationEngine` và `normalize_equation` nhận diện miền rỗng ngay tại Bước 1, không thực thi các phép biến đổi mẫu số 0, kết luận ngay phương trình vô nghiệm trên $\mathbb{R}$ với trạng thái chứng minh `SOUND_AND_COMPLETE_IN_SCOPE`, `verified_roots = []`.
- **Minh chứng kiểm thử:**
  - `test_r3_constant_zero_division_empty_domain`: `x / 0 = 0` $\implies$ Miền $\emptyset$, không có nghiệm thực, chứng minh hoàn tất.
  - `test_r3_identically_zero_polynomial_denominator`: `1 / (x - x) = 0` $\implies$ Miền $\emptyset$, không có nghiệm thực.
  - `test_r3_domain_contains_returns_false_on_empty_domain`: Mọi giá trị kiểm tra đều trả về `False`.

---

### R4. Kiểm soát tăng trưởng biểu thức trung gian & Bậc đa thức (Resource Bounds & Growth)

- **Hiện tượng lỗi gốc:**
  Quá trình khai triển phương trình có thể tạo ra các đa thức có bậc hoặc hệ số trung gian vượt quá giới hạn tài nguyên của bài toán đại số sơ cấp (ví dụ: phương trình tích có bậc sau khai triển lên tới 8).
- **Giải pháp khắc phục:**
  1. Tại giai đoạn Lexer: Bắt lỗi trực tiếp các hằng số số học vượt ngưỡng `max_coefficient_magnitude` $\to$ ném `CoefficientMagnitudeError`.
  2. Tại giai đoạn Chuẩn hóa (`normalize_equation`):
     - Kiểm tra bậc đa thức tử số và mẫu số sau khai triển: nếu bậc $> 4$ (ví dụ: $x^4 \cdot x^4 = 0$ có bậc 8), ném ngoại lệ `OutOfScopeSyntaxError` một cách an toàn, hệ thống ghi nhận `OUT_OF_SCOPE` mà không ném lỗi unhandled exception.
     - Kiểm tra độ lớn hệ số sau khi khai triển (tích các hệ số nhỏ có thể tạo ra hệ số lớn): nếu hệ số khai triển vượt ngưỡng, ném `CoefficientMagnitudeError`.
- **Minh chứng kiểm thử:**
  - `test_r4_high_degree_rejection_out_of_scope`: $x^4 \cdot x^4 = 0$ trả về an toàn `is_verified_method = False`, `explanation` chứa `OUT_OF_SCOPE: Equation polynomial degree 8 exceeds maximum supported degree 4`.
  - `test_r4_coefficient_magnitude_limit`: Kiểm tra cả hai lớp chặn hệ số từ Lexer và Normalizer.

---

### R5. Tinh chỉnh phương pháp M5: Ràng buộc dấu đại số và sắp xếp nghiệm an toàn

- **Hiện tượng lỗi gốc:**
  1. Trong M5 (`m5_biquadratic.py`), việc kiểm tra điều kiện nghiệm phụ $t \ge 0$ sử dụng `float(sympy.N(t_val)) >= -1e-12`, dễ sai lệch khi gặp nghiệm rất gần 0 hoặc nghiệm số phức.
  2. Việc sắp xếp nghiệm `valid_x_roots` dùng `key=lambda val: float(val.evalf())`, sẽ làm sập chương trình với lỗi `TypeError` nếu biểu thức có thành phần ảo.
- **Giải pháp khắc phục:**
  1. Xác định dấu đại số chính xác cho $t$:
     - Dùng các thuộc tính hình thức của SymPy: `t_val.is_nonnegative`, `t_val.is_negative`, `sympy.sign(t_val)`.
     - Nếu dấu không thể xác định hình thức (undecidable), đánh dấu trạng thái `UNDECIDABLE`, chuyển nghĩa vụ chứng minh `SIGN_CONSTRAINT` và `COMPLETENESS` thành `UNRESOLVED` (không bao giờ giả định bừa bãi).
  2. Chỉ khôi phục nghiệm thực $x = \pm \sqrt{t}$ khi $t \ge 0$ một cách chắc chắn.
  3. Xây dựng hàm trích xuất khóa sắp xếp an toàn `_safe_sort_key`:
     - Nếu giá trị là thực: trích xuất giá trị thực dấu phẩy động để sắp xếp thứ tự.
     - Nếu có phần ảo hoặc không thể đánh giá: sắp xếp an toàn theo chuỗi đại số, tuyệt đối không gọi `float(complex)` gây sập chương trình.
- **Minh chứng kiểm thử:**
  - `test_r5_m5_symbolic_sign_all_negative`: $x^4 + 5x^2 + 4 = 0 \implies t = -1, -4 < 0 \implies$ Tập nghiệm thực rỗng, nghĩa vụ dấu đạt `PASS`.
  - `test_r5_m5_safe_sorting_no_complex_crash`: Phương trình đại số có căn bậc bốn $x^4 - 2 = 0 \implies x = \pm \sqrt[4]{2}$ được sắp xếp an toàn, không có lỗi runtime.

---

### R6. Loại bỏ 100% đường dẫn gọi `sympify()` không an toàn

- **Hiện tượng lỗi gốc:**
  Mặc dù Parser chính không dùng `sympify()`, nhưng trong các module phụ trợ vẫn còn tồn tại các lời gọi `sympy.sympify()` trên chuỗi đầu vào:
  - `src/mke/verification/transfer.py`: `sym_r = sympy.sympify(r_raw)`
  - `src/mke/models/domain.py`: `sym_val = sympy.sympify(x_val)`
  - `src/mke/methods/m2_quadratic.py`: `delta_val = sympy.sympify(delta_str)`
  Điều này tiềm ẩn nguy cơ thực thi mã độc hại nếu chuỗi truyền vào chứa các hàm dựng sẵn của Python.
- **Giải pháp khắc phục:**
  1. Trong `transfer.py`: Triển khai hàm `safe_parse_candidate_root(r_raw)`. Nếu là chuỗi, ưu tiên phân tích bằng `Fraction(s)`. Nếu là biểu thức toán học, gọi `Parser.from_text(s).parse_expression()` và `ast_to_sympy()`. Tuyệt đối không dùng `eval`, `exec` hay `sympify`. Các chuỗi chứa ký tự độc hại (`__import__`, `eval`, v.v.) sẽ bị bộ phân tích ngữ pháp chặn ngay lập tức.
  2. Trong `domain.py`: Chuyển đổi an toàn qua `Fraction` hoặc cấu tử SymPy định kiểu tường minh; từ chối mọi chuỗi độc hại mà không gọi `sympify`.
  3. Trong `m2_quadratic.py`: Tính toán trực tiếp $\Delta = b^2 - 4ac$ từ các hệ số đại số chính xác của phương trình đã chuẩn hóa, loại bỏ hoàn toàn việc ép kiểu ngược từ chuỗi.
- **Minh chứng kiểm thử:**
  - `test_r6_transfer_rejects_code_injection_strings`: Chuyển giao các chuỗi tấn công `__import__('os').system('calc')`, `eval('2+2')`, `exec(...)` $\implies$ Toàn bộ bị từ chối sạch sẽ với nhãn `UNSAFE_COPY`, không có bất kỳ dòng lệnh nào bị thực thi.
  - `test_r6_domain_contains_rejects_code_injection_strings`: `domain.contains()` từ chối chuỗi độc hại an toàn, trả về `False`.

---

## 3. TỔNG HỢP KIỂM THỬ THỰC TẾ & BẢO ĐẢM TÁI LẬP (REPRODUCIBILITY)

### Kết quả chạy kiểm thử toàn diện (`pytest -v`):
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Math Knowledge Engine
configfile: pyproject.toml
testpaths: tests
collected 97 items

tests\integration\test_pipeline.py ...                                   [  3%]
tests\property\test_properties.py .........................              [ 28%]
tests\security\test_security.py ............                             [ 41%]
tests\smoke\test_smoke_cases.py .........                                [ 50%]
tests\unit\test_audit_counter_cases.py .......                           [ 57%]
tests\unit\test_domain.py ...                                            [ 60%]
tests\unit\test_lexer.py .........                                       [ 70%]
tests\unit\test_methods.py .....                                         [ 75%]
tests\unit\test_obligations.py ...                                       [ 78%]
tests\unit\test_parser.py ......                                         [ 84%]
tests\unit\test_r1_r6_regression.py ...............                      [100%]

============================= 97 passed in 0.73s ==============================
```

### Kết quả chạy bộ Smoke Test Handcrafted (`mke smoke`):
```text
Executing Handcrafted Smoke Test Suite (T1 - T8)...

             Smoke Suite Summary (Total: 8, Passed: 8, Failed: 0)              
+-----------------------------------------------------------------------------+
| ID | Test Case Name          | Equation                | Status | Duration  |
|----+-------------------------+-------------------------+--------+-----------|
| T1 | Standard quadratic      | x^2 - 5*x + 6 = 0       | PASS   | 45.12 ms  |
| T2 | Rational equation       | (x^2 - 5*x + 6) / (x-2) | PASS   | 138.80 ms |
| T3 | Rational identity       | (x - 2) / (x - 2) = 1   | PASS   | 5.89 ms   |
| T4 | Zero-product factor     | x * (x - 1) = 0         | PASS   | 5.12 ms   |
| T5 | Quadratic with a=0      | 0 * x^2 + 2 * x - 4 = 0 | PASS   | 3.20 ms   |
| T6 | Biquadratic substitution| x^4 + x^2 - 2 = 0       | PASS   | 3.65 ms   |
| T7 | Quadratic Delta < 0     | x^2 + 1 = 0             | PASS   | 2.15 ms   |
| T8 | Out-of-scope radical    | sqrt(x + 2) = x         | PASS   | 0.04 ms   |
+-----------------------------------------------------------------------------+
Total Execution Time: 254.05 ms
```

---

## 4. DANH MỤC TỆP TIN THAY ĐỔI & TẠO MỚI

| STT | Đường dẫn tệp tin | Thao tác | Mô tả nội dung thay đổi |
|:---:|:---|:---:|:---|
| 1 | `src/mke/models/ast_nodes.py` | Chỉnh sửa | Cập nhật `to_math_string()` xử lý đúng mức ưu tiên lũy thừa và ngoặc đơn |
| 2 | `src/mke/parsing/parser.py` | Chỉnh sửa | Đảo ngược thứ tự phân tích: lũy thừa `^` liên kết chặt hơn dấu trừ `-` |
| 3 | `src/mke/models/domain.py` | Chỉnh sửa | Bổ sung `is_empty_domain`, `is_undetermined`, loại bỏ epsilon `1e-12`, loại bỏ `sympify` |
| 4 | `src/mke/domain/extractor.py` | Chỉnh sửa | Nhận diện mẫu số đồng nhất 0, mô hình hóa miền rỗng `\emptyset` chuẩn xác |
| 5 | `src/mke/parsing/normalizer.py` | Chỉnh sửa | Xử lý an toàn khi gặp miền rỗng; kiểm soát độ lớn hệ số đa thức sau khai triển |
| 6 | `src/mke/methods/m5_biquadratic.py` | Chỉnh sửa | Đánh giá dấu $t \ge 0$ bằng đại số hình thức; sắp xếp nghiệm không gây lỗi số phức |
| 7 | `src/mke/verification/transfer.py` | Chỉnh sửa | Thay `sympify` bằng `safe_parse_candidate_root` qua Parser an toàn |
| 8 | `src/mke/methods/m2_quadratic.py` | Chỉnh sửa | Tính $\Delta$ trực tiếp từ hệ số đại số, loại bỏ `sympify(delta_str)` |
| 9 | `src/mke/methods/m3_factorization.py`| Chỉnh sửa | Sắp xếp nghiệm an toàn; kiểm tra tính đầy đủ phụ thuộc trạng thái miền xác định |
| 10 | `src/mke/methods/m4_rational.py` | Chỉnh sửa | Sắp xếp nghiệm an toàn; kiểm tra tính đầy đủ phụ thuộc trạng thái miền xác định |
| 11 | `src/mke/verification/engine.py` | Chỉnh sửa | Xử lý miền rỗng trả về ngay vô nghiệm có chứng minh; chặn completeness khi miền undetermined |
| 12 | `src/mke/audit/audit_reporter.py` | Chỉnh sửa | Bổ sung mục kiểm toán R1–R6 và nâng phiên bản báo cáo lên `DEV-01-R1` |
| 13 | `tests/unit/test_r1_r6_regression.py` | Tạo mới | Bộ 15 bài kiểm thử hồi quy độc lập cho toàn bộ các phát hiện R1–R6 |
| 14 | `reports/DEV01_R1_AUDIT.json` | Tạo mới | Dữ liệu kiểm toán cấu trúc JSON chi tiết phiên bản DEV-01-R1 |

---

## 5. KẾT LUẬN & ĐỀ NGHỊ

1. Nhiệm vụ **DEV-01-R1** đã hoàn thành 100% mục tiêu kỹ thuật. Tất cả 6 trường hợp phản biện và lỗi kiểm toán đã được sửa chữa tận gốc tại tầng mô hình và thuật toán, không dùng mẹo chắp vá (workarounds).
2. Hệ sinh thái kiểm thử đạt độ tin cậy cao: **97/97 tests pass**, 8/8 smoke tests pass, 0 lỗi cảnh báo, 0 lỗ hổng injection.
3. Kính trình Người điều phối nghiệm thu độc lập phiên bản **DEV-01-R1** trên nhánh `dev01-r1-audit-fixes`.
4. Sau khi có biên bản nghiệm thu đạt 100%, nhóm nghiên cứu sẵn sàng tiếp nhận đề bài kế tiếp (DEV-02) theo đúng lộ trình đề tài.
