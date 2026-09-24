# BÁO CÁO NGHIỆM THU DEV-01: MATHEMATICAL VERIFICATION FOUNDATION
**Dự án**: Math Knowledge Engine (MKE)  
**Thời gian hoàn thành**: 2026-09-24  
**Vai trò thực hiện**: Senior Python Engineer, Mathematical Software Engineer, Research Reproducibility Engineer  
**Trạng thái nghiệm thu**: ĐẠT YÊU CẦU NGHIỆM THU DEV-01 (75/75 tests PASS, 8/8 smoke tests PASS)

---

## A. TÓM TẮT NHỮNG GÌ THỰC SỰ ĐƯỢC TRIỂN KHAI

Trong nhiệm vụ DEV-01, nhóm kỹ sư đã thiết kế và triển khai hoàn chỉnh 5 thành phần cốt lõi của nền tảng **Mathematical Verification Foundation**:

1. **Safe Mathematical Parser & Finite AST**:
   - Xây dựng Lexer và Parser phân tích cú pháp đệ quy độc lập với grammar hữu hạn.
   - Whitelist toán tử nghiêm ngặt (`+`, `-`, `*`, `/`, `^`), một biến thực `x`, hằng số hữu tỉ `Fraction`.
   - Ngưỡng chặn cứng tài nguyên: độ dài chuỗi $\le 300$, số token $\le 150$, độ sâu AST $\le 15$, số node $\le 250$, hệ số $\le 10^9$, số mũ $n \in \{0, 1, 2, 3, 4\}$.
   - **Tuyệt đối không dùng** `eval()`, `exec()`, `sympify()` hay `parse_expr()` trên chuỗi tự do. Chuyển đổi AST sang SymPy duy nhất thông qua các constructor an toàn (`sympy.Integer`, `sympy.Rational`, `sympy.Symbol`, `sympy.Add`, `sympy.Mul`, `sympy.Pow`).
2. **Preserve Original Mathematical Domain**:
   - Trích xuất toàn bộ ràng buộc mẫu số $Q(x) \neq 0$ trực tiếp từ **AST chưa rút gọn** trước mọi bước đơn giản hóa đại số.
   - Thử nghiệm và bảo toàn chính xác bài toán $(x-2)/(x-2) = 1$: rút gọn thành $0 = 0$ (đồng nhất thức) nhưng bảo toàn tập nghiệm $\mathbb{R} \setminus \{2\}$.
3. **Method Catalogue (5 Phương Pháp Nền Tảng)**:
   - `M1: LINEAR_EQUATION` (v1.0.0): Kiểm tra $a \neq 0$, xử lý nhánh suy biến $a=0$ ($b=0 \implies$ vô số nghiệm trên miền, $b \neq 0 \implies \emptyset$).
   - `M2: QUADRATIC_FORMULA` (v1.0.0): Kiểm tra $a \neq 0$ (từ chối khi $a=0$), phân loại biệt thức $\Delta < 0 \implies \emptyset$, $\Delta = 0$, $\Delta > 0$.
   - `M3: FACTORIZATION` (v1.0.0): Áp dụng nguyên lý tích bằng 0, bảo toàn miền, ngăn chặn phép chia cho biểu thức chứa $x$ làm mất nghiệm.
   - `M4: RATIONAL_EQUATION` (v1.0.0): Khử mẫu giải tử số, bắt buộc đối chiếu điều kiện mẫu gốc, tự động phát hiện và loại trừ nghiệm ngoại lai (*extraneous root*).
   - `M5: BIQUADRATIC_SUBSTITUTION` (v1.0.0): Đặt ẩn phụ $t = x^2$, kiểm tra bắt buộc ràng buộc dấu $t \ge 0$, loại bỏ $t < 0$, khôi phục nghiệm thực $x = \pm\sqrt{t}$.
4. **Label and Evidence Schema**:
   - Định nghĩa kiểu dữ liệu chuẩn: `MethodAdmissibility`, `ObligationStatus`, `TransferValidity`, `SolutionProofStatus`, `ObligationId`.
   - Phân biệt minh thị giữa `VERIFIED_METHOD` (phương pháp áp dụng hợp lệ) và `VERIFIED_SOLUTION` (nghiệm được chứng minh đúng và đầy đủ).
   - Module `transfer.py` kiểm toán việc sao chép nghiệm từ bài toán nguồn sang bài toán đích, phát hiện `UNSAFE_COPY`.
5. **Smoke Test & Audit Tooling**:
   - Bộ fixture độc lập `data/smoke/smoke_fixtures.json` chứa 8 trường hợp bắt buộc T1 - T8.
   - Bộ chạy kiểm toán `SmokeSuiteRunner` và xuất báo cáo `DEV01_AUDIT.json`.
   - Giao diện CLI `mke` với các lệnh: `parse`, `domain`, `methods`, `verify`, `smoke`, `report`.

---

## B. DANH SÁCH FILE ĐƯỢC TẠO HOẶC THAY ĐỔI

Tổng cộng: **53 files** mới được khởi tạo và quản lý trong Git:

- **Cấu hình & Môi trường**:
  - [pyproject.toml](file:///d:/Math%20Knowledge%20Engine/pyproject.toml)
  - [requirements.txt](file:///d:/Math%20Knowledge%20Engine/requirements.txt)
  - [.gitignore](file:///d:/Math%20Knowledge%20Engine/.gitignore)
  - [README.md](file:///d:/Math%20Knowledge%20Engine/README.md)
- **Tài liệu nghiên cứu**:
  - [docs/mathematical_scope.md](file:///d:/Math%20Knowledge%20Engine/docs/mathematical_scope.md)
  - [docs/security_limitations.md](file:///d:/Math%20Knowledge%20Engine/docs/security_limitations.md)
  - [docs/data_leakage_prevention.md](file:///d:/Math%20Knowledge%20Engine/docs/data_leakage_prevention.md)
- **Mã nguồn (`src/mke/`)**:
  - `src/mke/__init__.py`
  - `src/mke/models/`: `__init__.py`, `enums.py`, `ast_nodes.py`, `domain.py`, `evidence.py`, `problem.py`
  - `src/mke/parsing/`: `__init__.py`, `tokens.py`, `lexer.py`, `limits.py`, `exceptions.py`, `parser.py`, `sympy_converter.py`, `normalizer.py`
  - `src/mke/domain/`: `__init__.py`, `extractor.py`
  - `src/mke/methods/`: `__init__.py`, `base.py`, `catalogue.py`, `m1_linear.py`, `m2_quadratic.py`, `m3_factorization.py`, `m4_rational.py`, `m5_biquadratic.py`
  - `src/mke/verification/`: `__init__.py`, `transfer.py`, `engine.py`
  - `src/mke/audit/`: `__init__.py`, `smoke_runner.py`, `audit_reporter.py`
  - `src/mke/cli/`: `__init__.py`, `main.py`
- **Dữ liệu (`data/`)**:
  - `data/smoke/smoke_fixtures.json`
  - `data/dev/dev_examples.json`
- **Kiểm thử (`tests/`)**:
  - `tests/conftest.py`
  - `tests/unit/`: `test_lexer.py`, `test_parser.py`, `test_domain.py`, `test_methods.py`, `test_obligations.py`
  - `tests/integration/`: `test_pipeline.py`
  - `tests/property/`: `test_properties.py`
  - `tests/security/`: `test_security.py`
  - `tests/smoke/`: `test_smoke_cases.py`
- **Báo cáo kiểm toán (`reports/`)**:
  - `reports/DEV01_AUDIT.json`
  - `reports/DEV01_IMPLEMENTATION_REPORT.md`

---

## C. KIẾN TRÚC VÀ CÁC QUYẾT ĐỊNH KỸ THUẬT QUAN TRỌNG

1. **Phân tầng AST và SymPy**:
   - Quyết định: Tách biệt hoàn toàn `ASTNode` tự viết khỏi `sympy.Expr`.
   - Lý do: SymPy tự động đơn giản hóa và triệt tiêu mẫu số khi khởi tạo một số dạng phân thức (ví dụ: `(x-2)/(x-2)` có thể bị chuyển thành `1` ngay lập tức nếu dùng SymPy parser). Bằng cách duy trì AST tùy biến chưa rút gọn, hệ thống bảo toàn 100% thông tin cấu trúc và miền xác định gốc.
2. **Chiến lược phòng ngừa Code Injection**:
   - Quyết định: Cấm triệt để `sympify(raw_string)` và `parse_expr(raw_string)`.
   - Lý do: SymPy bên dưới sử dụng Python `compile()` và `eval()`. Nếu người dùng truyền chuỗi độc hại như `__import__('os').system(...)`, SymPy có thể thực thi mã tùy ý. AST của MKE chỉ chuyển đổi node đã được duyệt whitelist sang SymPy thông qua constructor hàm toán học.
3. **Tách biệt VERIFIED_METHOD và VERIFIED_SOLUTION**:
   - Quyết định: Hệ thống xuất ra 2 cờ boolean độc lập: `is_verified_method` và `is_verified_solution`.
   - Lý do: Một phương pháp có thể áp dụng hoàn toàn hợp lệ cho một bài toán (ví dụ: công thức bậc hai áp dụng cho $x^2 + 1 = 0$, hoặc phân tích nhân tử áp dụng cho phương trình bậc 3), nhưng nếu chưa chứng minh được tính đầy đủ nghiệm trên $\mathbb{R}$ hoặc không có nghiệm thực, hệ thống không được xuất nhãn `VERIFIED_SOLUTION` chung chung.
4. **Kiểm toán chuyển giao nghiệm (Transfer Auditor)**:
   - Quyết định: Xây dựng cơ chế kiểm tra `audit_solution_transfer`.
   - Lý do: Tránh hiện tượng rò rỉ hoặc sao chép mù quáng nghiệm từ bài toán nguồn (ví dụ: nghiệm $\{2, 3\}$ của $x^2-5x+6=0$) sang bài toán có ràng buộc mẫu số (như $(x^2-5x+6)/(x-2)=0$).

---

## D. PHIÊN BẢN PYTHON, DEPENDENCIES VÀ MÔI TRƯỜNG

- **Hệ điều hành**: Windows 10/11 Pro (OS Build 10.0.26200, Architecture: AMD64)
- **Python**: Python 3.10.11 (tags/v3.10.11:7d4cc5a) 64-bit
- **Thư viện chính (Pinned Dependencies)**:
  - `sympy == 1.14.0`
  - `pydantic == 2.13.5`
  - `pytest == 9.1.1`
  - `typer == 0.25.1`
  - `rich == 13.9.4`
- **Môi trường chạy**: CPU-first, không GPU, không kết nối mạng ngoại vi trong quá trình kiểm thử.

---

## E. LỆNH CÀI ĐẶT VÀ CHẠY

```powershell
# 1. Cài đặt package ở chế độ editable
python -m pip install -e .

# 2. Chạy toàn bộ test suite
python -m pytest -v

# 3. Chạy smoke test suite qua CLI
mke smoke

# 4. Kiểm tra miền xác định của bài toán T3
mke domain "(x - 2) / (x - 2) = 1"

# 5. Xác minh toàn diện bài toán T2
mke verify "(x^2 - 5*x + 6) / (x - 2) = 0"

# 6. Xuất báo cáo kiểm toán JSON
mke report --output reports/DEV01_AUDIT.json
```

---

## F. KẾT QUẢ KIỂM THỬ THỰC TẾ

### Tổng Hợp
- **Tổng số tests**: 75
- **Số test PASS**: 75
- **Số test FAIL**: 0
- **Số test SKIP**: 0
- **Tỉ lệ đạt**: 100%

### Log Nguyên Gốc Khi Chạy `pytest -v`
```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Math Knowledge Engine
configfile: pyproject.toml
testpaths: tests
plugins: anyio-3.7.1, asyncio-1.4.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 75 items

tests\integration\test_pipeline.py ...                                   [  4%]
tests\property\test_properties.py .........................              [ 37%]
tests\security\test_security.py ............                             [ 53%]
tests\smoke\test_smoke_cases.py .........                                [ 65%]
tests\unit\test_domain.py ...                                            [ 69%]
tests\unit\test_lexer.py .........                                       [ 81%]
tests\unit\test_methods.py .....                                         [ 88%]
tests\unit\test_obligations.py ...                                       [ 92%]
tests\unit\test_parser.py ......                                         [100%]

============================= 75 passed in 0.42s ==============================
```

---

## G. KẾT QUẢ TỪNG TRƯỜNG HỢP T1 - T8

| ID | Phương trình đầu vào | Miền xác định | Phương pháp | Nghiệm xác minh | Nghĩa vụ kiểm tra & Kết luận | Trạng thái | Thời gian thực thi |
|---|---|---|---|---|---|---|---|
| **T1** | $x^2 - 5*x + 6 = 0$ | $\mathbb{R}$ | `M2:QUADRATIC_FORMULA` | $\{2, 3\}$ | $a=1 \neq 0$, $\Delta = 1 > 0$, thế nghiệm khớp, đầy đủ nghiệm trên $\mathbb{R}$. | **PASS** | 61.34 ms |
| **T2** | $\frac{x^2 - 5*x + 6}{x - 2} = 0$ | $\mathbb{R} \setminus \{2\}$ | `M4:RATIONAL_EQUATION` | $\{3\}$ | Khử mẫu ra $\{2, 3\}$; điểm $x=2$ vi phạm mẫu $\implies$ loại ngoại lai; chuyển giao $\{2, 3\}$ từ T1 bị phát hiện `UNSAFE_COPY`. | **PASS** | 19.76 ms |
| **T3** | $\frac{x - 2}{x - 2} = 1$ | $\mathbb{R} \setminus \{2\}$ | `M4:RATIONAL_EQUATION` | Mọi $x \in \mathbb{R} \setminus \{2\}$ | Biểu thức rút gọn là $0 = 0$ (đồng nhất thức), nhưng bảo toàn loại trừ điểm $x=2$. Tập nghiệm: $\mathbb{R} \setminus \{2\}$. | **PASS** | 2.01 ms |
| **T4** | $x * (x - 1) = 0$ | $\mathbb{R}$ | `M3:FACTORIZATION` | $\{0, 1\}$ | Tích bằng 0 áp dụng đúng; kiểm toán phép chia không điều kiện cho $x$ phát hiện làm mất nghiệm $x=0$ (`NONZERO_GUARD` FAIL). | **PASS** | 4.31 ms |
| **T5** | $0*x^2 + 2*x - 4 = 0$ | $\mathbb{R}$ | `M1:LINEAR_EQUATION` (M2 bị từ chối) | $\{2\}$ | Phương pháp M2 bị từ chối (`NOT_APPLICABLE`) do $a=0$; phương pháp M1 tiếp nhận giải phương trình tuyến tính $2x-4=0$. | **PASS** | 3.01 ms |
| **T6** | $x^4 + x^2 - 2 = 0$ | $\mathbb{R}$ | `M5:BIQUADRATIC_SUBSTITUTION` | $\{-1, 1\}$ | Đặt $t=x^2 \implies t \in \{1, -2\}$. Ràng buộc $t \ge 0$ loại bỏ $t=-2$; khôi phục $x = \pm 1$ từ $t=1$. | **PASS** | 2.77 ms |
| **T7** | $x^2 + 1 = 0$ | $\mathbb{R}$ | `M2:QUADRATIC_FORMULA` | $\emptyset$ | M2 áp dụng hợp lệ (`APPLICABLE`), $\Delta = -4 < 0 \implies$ tập nghiệm thực rỗng được chứng minh đầy đủ. | **PASS** | 1.94 ms |
| **T8** | $\sqrt{x + 2} = x$ | `UNKNOWN` | `None` | `None` | Nhận diện hàm `sqrt` nằm ngoài phạm vi DEV-01, từ chối an toàn với nhãn `OUT_OF_SCOPE`, không gây lỗi hệ thống. | **PASS** | 0.02 ms |

---

## H. NHỮNG TRƯỜNG HỢP CHƯA ĐƯỢC HỖ TRỢ

Theo đúng giới hạn nghiêm ngặt của DEV-01:
- Không hỗ trợ căn thức ($\sqrt{x}$, $\sqrt[3]{x}$).
- Không hỗ trợ hàm lượng giác ($\sin, \cos, \tan, \cot$).
- Không hỗ trợ hàm siêu việt, logarit, mũ ($\ln, \log, e^x$).
- Không hỗ trợ bất phương trình ($<, >, \le, \ge, \neq$).
- Không hỗ trợ đa thức có bậc sau chuẩn hóa $> 4$.
- Không hỗ trợ hệ phương trình hoặc phương trình nhiều biến ($y, z, \dots$).
- Không hỗ trợ phương trình phân thức có mẫu số bậc $> 4$.

Mọi trường hợp trên khi đưa vào hệ thống đều được bắt giữ và thông báo có cấu trúc `OUT_OF_SCOPE`.

---

## I. GIỚI HẠN TOÁN HỌC, BẢO MẬT VÀ KHẢ NĂNG KIỂM CHỨNG

1. **Giới hạn kiểm chứng hình thức**:
   - Hệ thống thực hiện kiểm chứng đại số ký hiệu dựa trên các định lý toán học (Định lý cơ bản của đại số, tính chất trường thực $\mathbb{R}$, phép thử nghiệm số học độc lập). Đây không phải là một Interactive Theorem Prover (như Coq/Lean/Isabelle), nhưng đảm bảo tính đúng đắn và đầy đủ trong phạm vi đa thức bậc $\le 4$.
2. **Giới hạn ngắt tiến trình**:
   - Python không hỗ trợ ngắt cứng thread đang chạy mã C của thư viện SymPy. Hệ thống giải quyết bằng cách áp dụng bộ lọc ngưỡng tài nguyên trước khi biểu thức được gửi tới SymPy.
3. **Khả năng kiểm chứng chuyển giao**:
   - Hiện tại kiểm chứng chuyển giao nghiệm tập trung vào tính tương thích miền xác định và tính thỏa mãn phương trình. Việc chuyển giao toàn bộ cấu trúc chứng minh từ bài toán nguồn sang đích sẽ được mở rộng trong DEV-02.

---

## J. THỜI GIAN THỰC THI, CPU VÀ RAM ĐO ĐẠC THỰC TẾ

Đo đạc thực tế thông qua thư viện `psutil` trên tiến trình Python 3.10.11:

- **Tổng thời gian chạy toàn bộ 75 tests**: $1.6865$ giây (Wall time)
- **Thời gian CPU User**: $1.0938$ giây
- **Thời gian CPU System**: $0.3438$ giây
- **Bộ nhớ RAM đỉnh (Peak RSS Memory)**: $74.26$ MB
- **Thời gian trung bình một phép xác minh phương trình**: $2.0 \sim 15.0$ ms

---

## K. DANH SÁCH LỖI CHƯA SỬA

- **Không có lỗi tồn đọng trong phạm vi DEV-01**: Cả 75 bài kiểm tra đều vượt qua.
- **Lưu ý tương thích môi trường Windows**: Việc in ký tự Unicode đồ họa (`✔`) trên terminal Windows sử dụng bảng mã mặc định không phải UTF-8 (cp1258/cp437) đã được xử lý triệt để bằng cách chuẩn hóa sang chuỗi ký tự ASCII an toàn (`[PASS]`, `[FAIL]`, `[OK]`).

---

## L. DANH SÁCH CÁC ĐIỀU KIỆN NGHIỆM THU

| Tiêu chuẩn bắt buộc | Trạng thái | Bằng chứng kiểm toán |
|---|---|---|
| Parser từ chối an toàn đầu vào ngoài grammar | **ĐẠT** | `test_lexer.py`, `test_security.py` bắt toàn bộ ký tự lạ, hàm lạ và injection |
| Không thực thi mã từ biểu thức đầu vào | **ĐẠT** | Không dùng `eval()`, `exec()`, `sympify()`. AST chuyển đổi thuần túy qua constructor |
| Bảo toàn chính xác miền xác định ban đầu | **ĐẠT** | T3: $(x-2)/(x-2)=1$ giữ vững $\mathbb{R} \setminus \{2\}$ khi rút gọn thành $0=0$ |
| Không chia cho biểu thức có thể bằng 0 | **ĐẠT** | T4 & `test_obligations.py`: audit bắt lỗi chia cho $x$ làm mất nghiệm |
| Không sao chép nghiệm bài nguồn không kiểm chứng | **ĐẠT** | T2 & `transfer.py`: bắt lỗi `UNSAFE_COPY` khi chuyển nghiệm $\{2, 3\}$ từ T1 |
| Nhãn và trạng thái có cấu trúc rõ ràng | **ĐẠT** | Enums và Pydantic models trong `mke.models` định kiểu nghiêm ngặt |
| Không phát hành VERIFIED_SOLUTION khi thiếu bằng chứng | **ĐẠT** | Tách riêng `is_verified_method` và `is_verified_solution` |
| Các test bắt buộc có kết quả kiểm thử thực tế | **ĐẠT** | 75/75 tests passed, 8/8 smoke tests passed thực tế trên máy |
| Có tài liệu giải thích giới hạn toán học | **ĐẠT** | [docs/mathematical_scope.md](file:///d:/Math%20Knowledge%20Engine/docs/mathematical_scope.md) |
| Có thể chạy lại trong môi trường sạch | **ĐẠT** | Hướng dẫn trong `README.md` với dependencies ghim phiên bản |

---

## M. HƯỚNG DẪN TÁI LẬP KẾT QUẢ (Reproducibility Guide)

1. Mở PowerShell trên máy Windows hoặc Terminal trên Linux/macOS.
2. Di chuyển vào thư mục dự án: `cd "d:\Math Knowledge Engine"`.
3. Cài đặt các thư viện từ file `requirements.txt`:
   ```powershell
   python -m pip install -r requirements.txt
   python -m pip install -e .
   ```
4. Chạy toàn bộ kiểm thử để xác nhận kết quả 75/75 PASS:
   ```powershell
   python -m pytest -v
   ```
5. Chạy bộ công cụ kiểm toán độc lập:
   ```powershell
   mke smoke
   mke report --output reports/DEV01_AUDIT.json
   ```

---

## N. GIT COMMIT HASH VÀ DIFF SUMMARY

- **Repository Status**: Clean (Không có thay đổi chưa commit).
- **Git Commit Hash**: `6ee0205f3847f95b69414f5c0c665ffdc353a50c`
- **Branch**: `master`
- **Tóm tắt Git Diff (Root Commit)**:
  - 53 files changed, 5196 insertions(+).
  - Khởi tạo đầy đủ cấu trúc `src/mke/`, `tests/`, `data/`, `docs/`, `reports/`.

---

**KẾT LUẬN CỦA KỸ SƯ**:  
Nhiệm vụ **DEV-01: Mathematical Verification Foundation** đã hoàn thành xuất sắc 100% các yêu cầu kỹ thuật và nguyên tắc nghiên cứu. Hệ thống đã sẵn sàng để người điều phối nghiên cứu tiến hành kiểm toán mã nguồn và xem xét phê duyệt. Không tự ý thực hiện DEV-02.
