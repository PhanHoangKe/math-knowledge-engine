# BÁO CÁO KHẮC PHỤC DEV-01-R2: MATHEMATICAL SOUNDNESS & AST PRESERVATION

**Dự án**: Math Knowledge Engine (MKE)  
**Đề tài**: Nghiên cứu và thực nghiệm truy xuất, tái sử dụng phương pháp giải phương trình đại số có kiểm tra điều kiện áp dụng và nghĩa vụ chứng minh  
**Giai đoạn**: DEV-01-R2 (Remediation 2 — Mathematical Soundness & AST Preservation)  
**Nhánh Git**: `dev01-r2-remediation`  
**Trạng thái kiểm thử**: 119/119 tests pass (100%), 8/8 smoke tests pass (100%), 6/6 independent recheck checks pass (100%)  
**Kỷ luật nghiên cứu**: Không tự tuyên bố nghiệm thu 100%; bàn giao hiện trạng kỹ thuật trung thực để người điều phối kiểm toán độc lập.

---

## 1. TỔNG QUAN VÀ BỐI CẢNH

Sau đợt kiểm toán độc lập DEV-01-R1, người điều phối đã phát hiện hai lỗi nghiêm trọng ảnh hưởng trực tiếp đến tính đúng đắn toán học (mathematical soundness) và ba vấn đề kỹ thuật bổ sung:
1. **Lỗi toán học M4**: `m4_rational.py` diễn giải kết quả `solveset` kiểu `Intersection` thành tập nghiệm rỗng, dẫn đến việc kết luận sai là phương trình $(x^4 - x - 1)/(x^2 + 1) = 0$ vô nghiệm, đồng thời gán nhãn chứng minh hoàn tất `COMPLETENESS = PASS` và `is_verified_solution = True`.
2. **Kiểm tra miền thực và truyền nghiệm**: `OriginalDomain.contains()` và `audit_solution_transfer()` chưa chủ động loại trừ các phần tử không thuộc trường số thực $\mathbb{R}$ (như đơn vị ảo `sympy.I`, số phức, hoặc biểu thức chứa biến tự do).
3. **Trạng thái trên tập xác định rỗng**: Khi $\mathcal{D} = \emptyset$ (như $x/0 = 0$), hệ thống gán `is_verified_method = True` dù thực tế không có phương pháp giải nào được áp dụng (`method_instance = None`).
4. **Phân loại lỗi tài nguyên và phạm vi**: Các lỗi vượt giới hạn tài nguyên bị gộp chung vào `SYNTAX_OR_LIMIT_ERROR` thay vì phân loại có cấu trúc rõ ràng.
5. **Bảo toàn cây cú pháp AST qua round-trip**: `to_math_string()` làm thay đổi cấu trúc cây AST đối với biểu thức có dấu ngoặc vế phải (`1 + (x - 2) = 0`, `x * (x / 2) = 0`) và số thập phân hữu hạn (`x + 0.25 = 0`).

Toàn bộ 5 vấn đề trên đã được phân tích nguồn gốc và khắc phục triệt để trong nhánh `dev01-r2-remediation`.

---

## 2. CHI TIẾT KHẮC PHỤC THEO 5 YÊU CẦU

### Yêu cầu 1: Kiểm chứng tính đầy đủ của M4 và phân loại kết quả `solveset`
- **Nguyên nhân gốc**: Khi giải tử số $P(x) = x^4 - x - 1 = 0$, SymPy `solveset(..., domain=sympy.S.Reals)` trả về kiểu `sympy.sets.sets.Intersection(Reals, FiniteSet(...))`. Trong mã cũ, khối `else` chỉ kiểm tra `if isinstance(sym_sol, sympy.FiniteSet):`, khiến `raw_roots` không nhận được phần tử nào. Sau đó, mã mặc định phát sinh `ProofObligation(ObligationId.COMPLETENESS, ObligationStatus.PASS)` và gán `is_verified_solution = True`. Đồng thời hàm `sympy.simplify()` bị treo (hang) khi cố rút gọn biểu thức căn bậc 4 Ferrari lồng nhau.
- **Giải pháp triển khai**:
  - Tại [`m4_rational.py`](file:///d:/Math%20Knowledge%20Engine/src/mke/methods/m4_rational.py):
    - Phân loại tường minh các kiểu tập hợp trả về từ `solveset`:
      - `EmptySet`: Tập rỗng thực sự $\implies$ `is_exhaustive_enumeration = True`.
      - `FiniteSet`: Kiểm tra từng phần tử bằng `is_proven_real_number`. Nếu tất cả là số thực $\implies$ `is_exhaustive_enumeration = True`.
      - `Intersection`: Trích xuất các nghiệm thực chứng minh được vào tập nghiệm thô, nhưng đánh dấu `is_exhaustive_enumeration = False` vì SymPy chưa rút gọn hoàn toàn được giao với $\mathbb{R}$.
      - `Union`, `ConditionSet`, `ImageSet`: Đánh dấu `is_exhaustive_enumeration = False`.
    - Khi `not is_exhaustive_enumeration`: Bắt buộc ghi nhận `ProofObligation(ObligationId.COMPLETENESS, ObligationStatus.UNRESOLVED)`.
    - Tại [`engine.py`](file:///d:/Math%20Knowledge%20Engine/src/mke/verification/engine.py): Khi tính đầy đủ chưa được chứng minh nhưng các nghiệm tìm được thỏa mãn phương trình, gán nhãn `solution_status = SolutionProofStatus.SOUND_PARTIAL` và `is_verified_solution = False`.
    - Thay thế phép rút gọn ký hiệu chậm bằng hàm [`check_root_satisfaction()`](file:///d:/Math%20Knowledge%20Engine/src/mke/models/domain.py): kết hợp kiểm tra đại số tức thời và tính toán độ chính xác cao 50 chữ số (`evalf(50) < 1e-25`), loại bỏ hoàn toàn hiện tượng treo bộ giải.
- **Kết quả nghiệm chứng trên $(x^4 - x - 1) / (x^2 + 1) = 0$**:
  - Tìm thấy chính xác 2 nghiệm thực ($x \approx 1.22074, x \approx -0.72449$).
  - Không kết luận vô nghiệm.
  - `is_verified_solution`: `False`.
  - `solution_status`: `SOUND_PARTIAL`.
  - `obligations`: `COMPLETENESS = UNRESOLVED`.
- **Kết quả nghiệm chứng trên $(x^4 + 1) / (x^2 + 1) = 0$**:
  - `solveset` trả về `EmptySet`.
  - `is_verified_solution`: `True`.
  - `solution_status`: `SOUND_AND_COMPLETE_IN_SCOPE`.
  - `obligations`: `COMPLETENESS = PASS`.

---

### Yêu cầu 2: Kiểm chứng tập xác định thực và từ chối nghiệm phức / biến tự do
- **Nguyên nhân gốc**: `OriginalDomain.contains()` trước đây chấp nhận các đối tượng SymPy không phải số thực nếu phép trừ không báo lỗi. `audit_solution_transfer()` chưa kiểm tra tính chất thực của nghiệm trước khi thẩm định chuyển giao.
- **Giải pháp triển khai**:
  - Xây dựng hàm chuẩn [`is_proven_real_number(sym_val: sympy.Basic) -> bool`](file:///d:/Math%20Knowledge%20Engine/src/mke/models/domain.py):
    1. Từ chối biểu thức có biến tự do (`len(sym_val.free_symbols) > 0`).
    2. Kiểm tra cờ `sym_val.is_real`.
    3. Từ chối nếu chứa đơn vị ảo `sympy.I` hoặc phần ảo có độ lớn $> 10^{-25}$.
    4. Kiểm tra phần thực và tính hữu hạn qua `evalf(50)`.
  - Cập nhật [`OriginalDomain.contains()`](file:///d:/Math%20Knowledge%20Engine/src/mke/models/domain.py): Bắt buộc `if not is_proven_real_number(sym_val): return False`.
  - Cập nhật [`audit_solution_transfer()`](file:///d:/Math%20Knowledge%20Engine/src/mke/verification/transfer.py): Kiểm tra `is_proven_real_number(sym_r)` trước khi thẩm định điều kiện tập xác định và phương trình mục tiêu.
- **Kết quả nghiệm chứng**:
  - `domain.contains(sympy.I)` $\implies$ `False`.
  - `domain.contains(sympy.Symbol('y'))` $\implies$ `False`.
  - Target $x^2 + 1 = 0$, chuyển giao nghiệm `sympy.I` $\implies$ Trả về `TransferValidity.UNSAFE_COPY`, danh sách `rejected_roots` ghi nhận rõ nguyên nhân không phải số thực trên $\mathbb{R}$.

---

### Yêu cầu 3: Nhất quán trạng thái kiểm chứng trên tập xác định rỗng
- **Nguyên nhân gốc**: Khi gặp phương trình có mẫu số triệt tiêu đồng nhất (như $x/0 = 0$ hoặc $1/(x - x) = 0$), tập xác định rỗng $\mathcal{D} = \emptyset$ dẫn đến tập nghiệm rỗng. Tuy nhiên [`engine.py`](file:///d:/Math%20Knowledge%20Engine/src/mke/verification/engine.py) trước đây thiết lập `is_verified_method = True` dù `method_instance = None`.
- **Giải pháp triển khai**:
  - Tại khối xử lý `if domain.is_empty_domain:` trong [`engine.py`](file:///d:/Math%20Knowledge%20Engine/src/mke/verification/engine.py):
    - Đặt tường minh `is_verified_method = False` vì không có phương pháp giải nào được áp dụng.
    - Giữ nguyên `is_verified_solution = True` vì tập nghiệm rỗng đã được chứng minh hoàn tất qua chứng cứ tập xác định (`domain evidence`).
    - Báo cáo rõ: *"Proven complete on domain: original domain is empty (division by zero detected in expression). Solution set is proven empty purely by domain evidence without applying any equation solving method."*
- **Kết quả nghiệm chứng**:
  - Phương trình $x/0 = 0$: `method_instance = None`, `is_verified_method = False`, `is_verified_solution = True`, `solution_status = SOUND_AND_COMPLETE_IN_SCOPE`.

---

### Yêu cầu 4: Phân loại lỗi vượt giới hạn tài nguyên và cú pháp
- **Nguyên nhân gốc**: `VerificationEngine.verify()` gom tất cả `ParserError` thành `SYNTAX_OR_LIMIT_ERROR`, làm mờ ranh giới giữa lỗi cú pháp sai, lỗi vượt ngưỡng an toàn DoS, lỗi ngoài phạm vi nghiên cứu và lỗi hệ thống.
- **Giải pháp triển khai**:
  - Định nghĩa nhóm lỗi tài nguyên `RESOURCE_LIMIT_ERRORS`:
    `InputLengthExceededError`, `TokenCountExceededError`, `ASTDepthExceededError`, `NodeCountExceededError`, `CoefficientMagnitudeError`, `InvalidExponentError`.
  - Tại [`engine.py`](file:///d:/Math%20Knowledge%20Engine/src/mke/verification/engine.py), bắt và phân loại thành 4 nhóm kết quả:
    1. `RESOURCE_LIMIT_ERRORS` $\implies$ `domain_str = "UNKNOWN (RESOURCE_LIMIT)"`, `explanation = f"RESOURCE_LIMIT: {type(e).__name__}: {e.message}"`.
    2. `OutOfScopeSyntaxError` $\implies$ `domain_str = "UNKNOWN (OUT_OF_SCOPE)"`, `explanation = f"OUT_OF_SCOPE: {e.message}"`.
    3. `InvalidSyntaxError` $\implies$ `domain_str = "UNKNOWN (SYNTAX_ERROR)"`, `explanation = f"SYNTAX_ERROR: {e.message}"`.
    4. `Exception` khác $\implies$ `domain_str = "UNKNOWN (INTERNAL_ERROR)"`, `explanation = f"INTERNAL_ERROR: {type(e).__name__}: {str(e)}"`.
  - Tất cả các trường hợp đều đảm bảo `is_verified_solution = False`, `is_verified_method = False`, `solution_status = UNDETERMINED`.
  - Giữ nguyên các ngưỡng an toàn tài nguyên mặc định, không hạ thấp giới hạn.
- **Kết quả nghiệm chứng**:
  - Độ dài vượt giới hạn $\implies$ `RESOURCE_LIMIT: InputLengthExceededError`.
  - Số lượng token vượt giới hạn $\implies$ `RESOURCE_LIMIT: TokenCountExceededError`.
  - Độ sâu AST vượt giới hạn $\implies$ `RESOURCE_LIMIT: ASTDepthExceededError`.
  - Độ lớn hệ số vượt giới hạn $\implies$ `RESOURCE_LIMIT: CoefficientMagnitudeError`.
  - Số mũ $> 4$ $\implies$ `RESOURCE_LIMIT: InvalidExponentError`.
  - Hàm lượng giác $\sin(x) = 0$ $\implies$ `OUT_OF_SCOPE`.
  - Cú pháp sai $x + = 0$ $\implies$ `SYNTAX_ERROR`.

---

### Yêu cầu 5: Bảo toàn cấu trúc cây AST khi round-trip
- **Nguyên nhân gốc**:
  - Toán tử nhị phân cùng độ ưu tiên ở vế phải (như `1 + (x - 2) = 0` hoặc `x * (x / 2) = 0`) bị mất dấu ngoặc do điều kiện đóng ngoặc cũ chỉ xét độ ưu tiên thực sự nhỏ hơn (`<`), bỏ qua tính kết hợp trái (left-associativity) của phép cộng/trừ và nhân/chia.
  - Hằng số thập phân hữu hạn (như `0.25`) bị chuyển thành phân số `1/4` khi gọi `to_math_string()`, dẫn đến khi phân tích cú pháp lại, nút `NumberNode` bị biến thành `BinaryOpNode('/')`.
- **Giải pháp triển khai**:
  - Tại [`ast_nodes.py`](file:///d:/Math%20Knowledge%20Engine/src/mke/models/ast_nodes.py):
    - Bổ sung trường `raw_literal: Optional[str] = None` vào `NumberNode`. Nếu có `raw_literal`, ưu tiên sử dụng `raw_literal`. Đồng thời bổ sung hàm định dạng số thập phân hữu hạn cho các phân số có mẫu số lũy thừa của 2 và 5.
    - Cập nhật [`Parser._parse_primary()`](file:///d:/Math%20Knowledge%20Engine/src/mke/parsing/parser.py): truyền trực tiếp chuỗi gốc từ token (`tok.value`) vào `raw_literal`.
    - Cập nhật `BinaryOpNode.to_math_string()`:
      ```python
      if self._precedence(self.right.op) <= self._precedence(self.op):
          right_str = f"({self.right.to_math_string()})"
      ```
      Bảo toàn dấu ngoặc khi toán tử vế phải có độ ưu tiên nhỏ hơn hoặc bằng toán tử hiện tại.
- **Kết quả nghiệm chứng**:
  - `1 + (x - 2) = 0` $\implies$ render: `1 + (x - 2) = 0` $\implies$ AST1 == AST2 (True).
  - `x + 0.25 = 0` $\implies$ render: `x + 0.25 = 0` $\implies$ AST1 == AST2 (True).
  - `x * (x / 2) = 0` $\implies$ render: `x * (x / 2) = 0` $\implies$ AST1 == AST2 (True).

---

## 3. TỔNG HỢP KIỂM THỬ VÀ TÁI HIỆN

### 3.1. Kết quả kiểm thử tự động toàn diện
```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Math Knowledge Engine
configfile: pyproject.toml
testpaths: tests
plugins: anyio-3.7.1, asyncio-1.4.0
collected 119 items

tests\integration\test_pipeline.py ...                                   [  2%]
tests\property\test_properties.py .........................              [ 23%]
tests\security\test_security.py ............                             [ 33%]
tests\smoke\test_smoke_cases.py .........                                [ 41%]
tests\unit\test_audit_counter_cases.py .......                           [ 47%]
tests\unit\test_domain.py ...                                            [ 49%]
tests\unit\test_lexer.py .........                                       [ 57%]
tests\unit\test_methods.py .....                                         [ 61%]
tests\unit\test_obligations.py ...                                       [ 63%]
tests\unit\test_parser.py ......                                         [ 68%]
tests\unit\test_r1_r6_regression.py ...............                      [ 81%]
tests\unit\test_r2_soundness_regression.py ......................        [100%]

============================= 119 passed in 2.74s =============================
```

### 3.2. Script kiểm toán độc lập `DATN_DEV01_R2_INDEPENDENT_RECHECK.py`
Người điều phối có thể trực tiếp thực thi:
```powershell
python DATN_DEV01_R2_INDEPENDENT_RECHECK.py
```
Kết quả thực tế:
```
================================================================================
DATN DEV-01-R2: INDEPENDENT MATHEMATICAL SOUNDNESS RECHECK
================================================================================

[CHECK 1/6] M4 Solveset Handling: (x^4 - x - 1) / (x^2 + 1) = 0
  PASS: Found 2 real roots, COMPLETENESS=UNRESOLVED, is_verified_solution=False, status=SOUND_PARTIAL.

[CHECK 2/6] M4 Truly Empty Root Proof: (x^4 + 1) / (x^2 + 1) = 0
  PASS: Formally proved empty set on R, COMPLETENESS=PASS, is_verified_solution=True.

[CHECK 3/6] Real Domain & Transfer Rejection: target x^2 + 1 = 0, candidate sympy.I
  PASS: sympy.I and free variables strictly rejected as UNSAFE_COPY. OriginalDomain.contains() returns False.

[CHECK 4/6] Empty Domain State Consistency: x / 0 = 0
  PASS: is_verified_method=False, is_verified_solution=True, method_instance=None. Proven purely by domain evidence.

[CHECK 5/6] Resource Limits & Error Classification
  PASS: Structured classification for RESOURCE_LIMIT, OUT_OF_SCOPE, and SYNTAX_ERROR verified without false verification.

[CHECK 6/6] AST Round-trip Structure Preservation
  PASS: All round-trip cases preserved exact AST trees: ['1 + (x - 2) = 0', 'x + 0.25 = 0', 'x * (x / 2) = 0']

================================================================================
SUMMARY: 6/6 independent recheck suites PASSED.
================================================================================
```

---

## 4. TÀI LIỆU VÀ CÔNG CỤ XUẤT BÁO CÁO

- Báo cáo kiểm toán máy đọc: [`reports/DEV01_R2_AUDIT.json`](file:///d:/Math%20Knowledge%20Engine/reports/DEV01_R2_AUDIT.json)
- Bộ kiểm thử hồi quy R2: [`tests/unit/test_r2_soundness_regression.py`](file:///d:/Math%20Knowledge%20Engine/tests/unit/test_r2_soundness_regression.py)
- Script kiểm tra độc lập: [`DATN_DEV01_R2_INDEPENDENT_RECHECK.py`](file:///d:/Math%20Knowledge%20Engine/DATN_DEV01_R2_INDEPENDENT_RECHECK.py)

---

## 5. CAM KẾT VÀ BÀN GIAO

1. **Tuân thủ phạm vi**: Toàn bộ công việc nằm nghiêm ngặt trong phạm vi DEV-01-R2. Không tự ý mở rộng sang DEV-02 (truy xuất tri thức, vector store, embedding), không tích hợp LLM, không xây dựng giao diện người dùng.
2. **Kỷ luật nghiên cứu**: Báo cáo phản ánh trung thực toàn bộ kết quả thực nghiệm. Không đưa ra tuyên bố hệ thống hoàn hảo tuyệt đối.
3. **Sẵn sàng kiểm toán**: Đề nghị Người điều phối độc lập thực hiện quy trình thẩm định để đánh giá nghiệm thu DEV-01-R2.
