# MKE PRODUCT-03B — THPT MATHEMATICAL CAPABILITY GAP AUDIT
## Comprehensive Source Inspection & Curriculum Coverage Matrix

**Author:** Antigravity (Implementation Engineer)  
**Baseline Commit:** `e207efcfd4d1af31e4e94202174f5d98e0bb5692` (Tag: `v0.3.0-p03b-accepted`)  
**Audited Subsystems:**
- `src/mke_product/parser/` (Lexer, AST, Parser)
- `src/mke_product/cas/` (CAS Parser, Safety, Bridge, Router, SymPy Adapter)
- `src/mke_product/solver/` (Native Affine Solver, Verification Engine)
- `src/mke_product/worker/` (Process Isolation, Sandboxing, UTF-8 Framing)
- `tests/` (All 479 Unit, Integration, and Browser Tests)

---

## 1. Executive Capability Audit Summary

```mermaid
pie title THPT Curriculum Archetype Coverage in Product 03B
    "IMPLEMENTED_AND_TESTED (7)" : 7
    "PARTIALLY_IMPLEMENTED (8)" : 8
    "IMPLEMENTED_BUT_UNVERIFIED (0)" : 0
    "NOT_IMPLEMENTED (87)" : 87
```

- **Total Mapped Archetypes:** 102
- **`IMPLEMENTED_AND_TESTED`:** 7 archetypes (6.9%)
- **`PARTIALLY_IMPLEMENTED`:** 8 archetypes (7.8%)
- **`IMPLEMENTED_BUT_UNVERIFIED`:** 0 archetypes (0.0%)
- **`NOT_IMPLEMENTED`:** 87 archetypes (85.3%)
- **`UNKNOWN`:** 0 archetypes (0.0%)

### Critical Audit Finding:
> **The isolated ability of SymPy to execute general CAS calls in tests does NOT constitute verified problem-family coverage.**
> In Product 03B, unsupported archetypes either fail at the parser level (syntax error), get rejected by safety checks (`OUT_OF_SCOPE`), lack dedicated mathematical representations/models, or return unformatted raw output without domain screening or verification evidence.

---

## 2. Detailed Archetype Coverage Matrix

### Grade 10 Mathematics (Lớp 10)

| Archetype ID | Archetype Description | Classification | Code Path / Mechanism | Test Evidence | Counterexample / Gap Analysis |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **`ARCH-10.1.1`** | Xét chân trị mệnh đề logic ($\forall, \exists$) | `NOT_IMPLEMENTED` | N/A | None | No logic AST or quantifier syntax in parser. |
| **`ARCH-10.1.2`** | Phép toán tập hợp số khoảng/đoạn | `NOT_IMPLEMENTED` | N/A | None | Set operations ($A \cap B, A \cup B$) not parsed. |
| **`ARCH-10.1.3`** | Tham số $m$ trong tập hợp | `NOT_IMPLEMENTED` | N/A | None | Parametric set solver nonexistent. |
| **`ARCH-10.2.1`** | Điểm thuộc miền nghiệm BPT 2 ẩn | `NOT_IMPLEMENTED` | N/A | None | Multi-variable inequality point evaluation not implemented. |
| **`ARCH-10.2.2`** | Xác định đỉnh miền đa giác nghiệm | `NOT_IMPLEMENTED` | N/A | None | 2D polyhedral vertex geometry nonexistent. |
| **`ARCH-10.2.3`** | Quy hoạch tuyến tính (Linear Programming) | `NOT_IMPLEMENTED` | N/A | None | Simplex/vertex optimization engine nonexistent. |
| **`ARCH-10.3.1`** | Tọa độ đỉnh, trục đối xứng parabol | `NOT_IMPLEMENTED` | N/A | None | Parabol feature extractor not implemented. |
| **`ARCH-10.3.2`** | Xác định hàm bậc 2 qua 3 điểm | `PARTIALLY_IMPLEMENTED` | Can be framed as 3x3 system in SymPy, but 3x3 systems are explicitly rejected as `OUT_OF_SCOPE`. | `test_solve_system_reject_original_ast_variable_bypass` | `OUT_OF_SCOPE` if input has $>2$ variables. |
| **`ARCH-10.3.3`** | Min/Max hàm bậc hai trên $[p; q]$ | `NOT_IMPLEMENTED` | N/A | None | Bounded domain optimization not supported. |
| **`ARCH-10.4.1`** | Giải BPT bậc hai 1 ẩn | `IMPLEMENTED_AND_TESTED` | `sympy_adapter.py::_execute_solve_inequality` | `test_solve_inequality_e2e_quadratic` | Degree $\le 2$ single-variable supported. |
| **`ARCH-10.4.2`** | Tham số $m$ trong tam thức bậc 2 | `NOT_IMPLEMENTED` | N/A | None | Parametric sign analysis ($a>0, \Delta<0$) nonexistent. |
| **`ARCH-10.4.3`** | BPT tích/thương hữu tỉ | `NOT_IMPLEMENTED` | `sympy_adapter.py` line 398 rejects variable denominators | `test_solve_inequality_reject_rational_fractions` | Variable denominators explicitly return `OUT_OF_SCOPE`. |
| **`ARCH-10.5.1`** | PT căn thức $\sqrt{f} = \sqrt{g}$ | `NOT_IMPLEMENTED` | Parser rejects `\sqrt` or `sqrt` in equation solver | None | Square root expressions not supported in equation parser. |
| **`ARCH-10.5.2`** | PT căn thức $\sqrt{f} = g(x)$ | `NOT_IMPLEMENTED` | Parser rejects square root in equations | None | Squaring with condition $g(x) \ge 0$ nonexistent. |
| **`ARCH-10.5.3`** | PT chứa giá trị tuyệt đối $\|f\| = g$ | `NOT_IMPLEMENTED` | Parser rejects $\|x\|$ | None | Absolute value branching nonexistent. |
| **`ARCH-10.6.1`** | Phương trình chứa $A_n^k, C_n^k$ | `NOT_IMPLEMENTED` | N/A | None | Combinatorial symbols not recognized in grammar. |
| **`ARCH-10.6.2`** | Bài toán đếm số phương án | `NOT_IMPLEMENTED` | N/A | None | Discrete combinatorics engine nonexistent. |
| **`ARCH-10.6.3`** | Khai triển Nhị thức Newton | `NOT_IMPLEMENTED` | N/A | None | Binomial coefficient expansion engine nonexistent. |
| **`ARCH-10.7.1`** | Hệ thức lượng trong tam giác | `NOT_IMPLEMENTED` | N/A | None | Triangle solver nonexistent. |
| **`ARCH-10.7.2`** | Diện tích tam giác (Heron/Sin) | `NOT_IMPLEMENTED` | N/A | None | Formula evaluator for geometric entities nonexistent. |
| **`ARCH-10.7.3`** | Bài toán thực tế đo đạc góc/cạnh | `NOT_IMPLEMENTED` | N/A | None | Applied word problem parser nonexistent. |
| **`ARCH-10.8.1`** | Phân tích vectơ 2D | `NOT_IMPLEMENTED` | N/A | None | 2D vector data types not implemented. |
| **`ARCH-10.8.2`** | Tích vô hướng $\vec{a} \cdot \vec{b}$ | `NOT_IMPLEMENTED` | N/A | None | Vector arithmetic nonexistent. |
| **`ARCH-10.8.3`** | Góc giữa 2 vectơ / Vuông góc | `NOT_IMPLEMENTED` | N/A | None | Vector angle engine nonexistent. |
| **`ARCH-10.9.1`** | Viết phương trình đường thẳng 2D | `NOT_IMPLEMENTED` | N/A | None | 2D Line geometry object nonexistent. |
| **`ARCH-10.9.2`** | Khoảng cách & Góc trong $Oxy$ | `NOT_IMPLEMENTED` | N/A | None | Distance/angle formula engine nonexistent. |
| **`ARCH-10.9.3`** | Phương trình đường tròn & tiếp tuyến | `NOT_IMPLEMENTED` | N/A | None | Circle geometry solver nonexistent. |
| **`ARCH-10.9.4`** | Ba đường Conic (Elip, Hypebol, Parabol) | `NOT_IMPLEMENTED` | N/A | None | Conic section analyzer nonexistent. |
| **`ARCH-10.10.1`** | Thống kê số trung bình, trung vị, tứ phân vị | `NOT_IMPLEMENTED` | N/A | None | Descriptive statistics engine nonexistent. |
| **`ARCH-10.10.2`** | Khoảng biến thiên, IQR, Outlier | `NOT_IMPLEMENTED` | N/A | None | Dispersion metrics nonexistent. |
| **`ARCH-10.10.3`** | Phương sai & Độ lệch chuẩn không ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Variance calculations nonexistent. |
| **`ARCH-10.11.1`** | Không gian mẫu phép thử | `NOT_IMPLEMENTED` | N/A | None | Probability sample space model nonexistent. |
| **`ARCH-10.11.2`** | Xác suất cổ điển biến cố | `NOT_IMPLEMENTED` | N/A | None | Combinatorial probability solver nonexistent. |
| **`ARCH-10.11.3`** | Xác suất biến cố đối / Hợp xung khắc | `NOT_IMPLEMENTED` | N/A | None | Probability algebra nonexistent. |
| **`ARCH-10.E1.1`** | Hệ PT bậc nhất 3 ẩn (Gauss) | `NOT_IMPLEMENTED` | Rejected by `sympy_adapter.py` line 290 | `test_solve_system_reject_multivariate` | Systems with $>2$ variables explicitly `OUT_OF_SCOPE`. |
| **`ARCH-10.E1.2`** | Quy nạp toán học | `NOT_IMPLEMENTED` | N/A | None | Automated inductive proof engine nonexistent. |
| **`ARCH-10.E1.3`** | Nhị thức Newton tổng quát | `NOT_IMPLEMENTED` | N/A | None | Generalized binomial expansion nonexistent. |
| **`ARCH-10.E2.1`** | Ứng dụng ba đường conic | `NOT_IMPLEMENTED` | N/A | None | Applied conic modeling nonexistent. |

---

### Grade 11 Mathematics (Lớp 11)

| Archetype ID | Archetype Description | Classification | Code Path / Mechanism | Test Evidence | Counterexample / Gap Analysis |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **`ARCH-11.1.1`** | Rút gọn biểu thức lượng giác | `PARTIALLY_IMPLEMENTED` | `_execute_simplify` via SymPy | None | SymPy simplifies elementary $\sin/\cos$, but trigonometric identity step explanations are absent. |
| **`ARCH-11.1.2`** | TXĐ & Chu kì hàm lượng giác | `NOT_IMPLEMENTED` | Safety engine rejects transcendental functions from domain audit | `test_domain_certainty_not_fully_determined` | Transcendental domain analysis returns `NOT_FULLY_DETERMINED`. |
| **`ARCH-11.1.3`** | PT lượng giác cơ bản | `PARTIALLY_IMPLEMENTED` | `_execute_solve` via SymPy | None | SymPy solves basic $\sin(x)=0$, but infinite solution family ($x_0 + k2\pi$) is not formatted cleanly into secondary school standards. |
| **`ARCH-11.1.4`** | PT $a\sin x + b\cos x = c$ & đếm nghiệm | `NOT_IMPLEMENTED` | N/A | None | Interval root counting for periodic functions not implemented. |
| **`ARCH-11.2.1`** | Dãy số & Tính tăng/giảm/bị chặn | `NOT_IMPLEMENTED` | N/A | None | Discrete sequence engine nonexistent. |
| **`ARCH-11.2.2`** | Cấp số cộng: $u_n, S_n$ | `NOT_IMPLEMENTED` | N/A | None | Arithmetic progression solver nonexistent. |
| **`ARCH-11.2.3`** | Cấp số nhân & Cấp số nhân lùi vô hạn | `NOT_IMPLEMENTED` | N/A | None | Geometric progression solver nonexistent. |
| **`ARCH-11.2.4`** | Bài toán thực tế lãi kép / Cấp số | `NOT_IMPLEMENTED` | N/A | None | Financial sequence model nonexistent. |
| **`ARCH-11.3.1`** | Giới hạn dãy số $\lim u_n$ | `NOT_IMPLEMENTED` | `OperationType.LIMIT` not in schema | None | Limit operation not supported in API or AST. |
| **`ARCH-11.3.2`** | Giới hạn hàm số dạng vô định $[0/0]$ | `NOT_IMPLEMENTED` | `OperationType.LIMIT` not supported | None | Limit computation not wired in router. |
| **`ARCH-11.3.3`** | Giới hạn một bên & Tính liên tục | `NOT_IMPLEMENTED` | N/A | None | Continuity verification engine nonexistent. |
| **`ARCH-11.3.4`** | Định lí giá trị trung gian (nghiệm PT) | `NOT_IMPLEMENTED` | N/A | None | Root existence theorem prover nonexistent. |
| **`ARCH-11.4.1`** | Rút gọn biểu thức mũ, logarit | `PARTIALLY_IMPLEMENTED` | `_execute_simplify` via SymPy | None | Basic SymPy simplification; no log law step breakdown. |
| **`ARCH-11.4.2`** | Tập xác định hàm số mũ/logarit | `NOT_IMPLEMENTED` | Safety engine rejects non-algebraic nodes | None | Logarithmic domain restriction extractor not implemented. |
| **`ARCH-11.4.3`** | Phương trình mũ và logarit | `PARTIALLY_IMPLEMENTED` | `_execute_solve` via SymPy | None | SymPy can find roots, but candidate domain verification and extraneous roots in log equations are unverified. |
| **`ARCH-11.4.4`** | Bất phương trình mũ và logarit | `NOT_IMPLEMENTED` | `_execute_solve_inequality` rejects non-polynomial AST | `test_solve_inequality_scope` | Inequalities with log/exp return `OUT_OF_SCOPE`. |
| **`ARCH-11.5.1`** | Đạo hàm hàm đa thức, lượng giác, exp/log | `IMPLEMENTED_AND_TESTED` | `_execute_differentiate` via SymPy | `test_differentiation_polynomial`, `test_differentiation_trigonometric` | Direct differentiation computed successfully. |
| **`ARCH-11.5.2`** | Tiếp tuyến tại điểm $M(x_0; y_0)$ | `NOT_IMPLEMENTED` | N/A | None | Tangent line equation builder not implemented. |
| **`ARCH-11.5.3`** | Tiếp tuyến biết hệ số góc $k$ | `NOT_IMPLEMENTED` | N/A | None | Derivative root to tangent solver nonexistent. |
| **`ARCH-11.5.4`** | Đạo hàm cấp hai & Vận tốc/Gia tốc | `PARTIALLY_IMPLEMENTED` | SymPy can differentiate twice, but second-order derivative API option is not wired | None | Second derivative option not exposed. |
| **`ARCH-11.6.1`** | Giao tuyến MP & Giao điểm đường/mặt 3D | `NOT_IMPLEMENTED` | N/A | None | Synthetic 3D geometry engine nonexistent. |
| **`ARCH-11.6.2`** | Chứng minh song song trong không gian | `NOT_IMPLEMENTED` | N/A | None | Geometric proof engine nonexistent. |
| **`ARCH-11.6.3`** | Thiết diện hình không gian | `NOT_IMPLEMENTED` | N/A | None | 3D cross-section geometry nonexistent. |
| **`ARCH-11.7.1`** | Chứng minh vuông góc $d \perp (\alpha)$ | `NOT_IMPLEMENTED` | N/A | None | 3D perpendicularity engine nonexistent. |
| **`ARCH-11.7.2`** | Góc giữa đường thẳng và mặt phẳng | `NOT_IMPLEMENTED` | N/A | None | 3D angle solver nonexistent. |
| **`ARCH-11.7.3`** | Góc phẳng nhị diện trong hình chóp | `NOT_IMPLEMENTED` | N/A | None | Dihedral angle solver nonexistent. |
| **`ARCH-11.7.4`** | Khoảng cách điểm đến MP & 2 đường chéo nhau | `NOT_IMPLEMENTED` | N/A | None | Synthetic 3D distance solver nonexistent. |
| **`ARCH-11.8.1`** | Số trung bình mẫu số liệu ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Grouped data statistics nonexistent. |
| **`ARCH-11.8.2`** | Trung vị & Tứ phân vị mẫu ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Grouped quantile engine nonexistent. |
| **`ARCH-11.8.3`** | Mốt mẫu số liệu ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Grouped mode engine nonexistent. |
| **`ARCH-11.9.1`** | Tính độc lập của hai biến cố | `NOT_IMPLEMENTED` | N/A | None | Event independence checker nonexistent. |
| **`ARCH-11.9.2`** | Xác suất giao & hợp biến cố độc lập | `NOT_IMPLEMENTED` | N/A | None | Probability algebra nonexistent. |
| **`ARCH-11.9.3`** | Bài toán xác suất thực tế | `NOT_IMPLEMENTED` | N/A | None | Applied probability modeler nonexistent. |
| **`ARCH-11.E1.1`** | Phép biến hình trong mặt phẳng | `NOT_IMPLEMENTED` | N/A | None | Geometric transformation engine nonexistent. |
| **`ARCH-11.E2.1`** | Bài toán tài chính (Lãi kép, niên kim) | `NOT_IMPLEMENTED` | N/A | None | Financial math solver nonexistent. |
| **`ARCH-11.E3.1`** | Lý thuyết đồ thị cơ bản | `NOT_IMPLEMENTED` | N/A | None | Graph theory engine nonexistent. |

---

### Grade 12 Mathematics (Lớp 12)

| Archetype ID | Archetype Description | Classification | Code Path / Mechanism | Test Evidence | Counterexample / Gap Analysis |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **`ARCH-12.1.1`** | Tính đơn điệu & Cực trị hàm số | `PARTIALLY_IMPLEMENTED` | Derivatives computed, but monotonicity interval & extrema analyzer not implemented | `test_differentiation_polynomial` | No extrema categorization or sign table. |
| **`ARCH-12.1.2`** | GTLN/GTNN trên đoạn $[a; b]$ | `NOT_IMPLEMENTED` | N/A | None | Optimization on closed intervals nonexistent. |
| **`ARCH-12.1.3`** | Tiệm cận đứng, ngang, xiên | `NOT_IMPLEMENTED` | N/A | None | Asymptote extraction engine nonexistent. |
| **`ARCH-12.1.4`** | Nhận dạng hàm số từ đồ thị | `NOT_IMPLEMENTED` | N/A | None | Inverse graph recognition nonexistent. |
| **`ARCH-12.1.5`** | Tham số $m$ trong khảo sát hàm số | `NOT_IMPLEMENTED` | N/A | None | Parametric calculus nonexistent. |
| **`ARCH-12.1.6`** | Bài toán tối ưu hóa thực tế | `NOT_IMPLEMENTED` | N/A | None | Applied calculus modeler nonexistent. |
| **`ARCH-12.2.1`** | Nguyên hàm cơ bản | `IMPLEMENTED_AND_TESTED` | `_execute_integrate` via SymPy | `test_integration_polynomial`, `test_integration_rational` | Indefinite integral computed. |
| **`ARCH-12.2.2`** | Nguyên hàm/Tích phân đổi biến | `PARTIALLY_IMPLEMENTED` | Final integral computed; step-by-step substitution $u(x)$ absent | None | Step breakdown absent. |
| **`ARCH-12.2.3`** | Nguyên hàm/Tích phân từng phần | `PARTIALLY_IMPLEMENTED` | Final integral computed; step-by-step $u, v$ absent | None | Step breakdown absent. |
| **`ARCH-12.2.4`** | Diện tích hình phẳng giới hạn bởi đồ thị | `NOT_IMPLEMENTED` | Intersection solving + multi-piece definite integral pipeline not wired | None | Area between curves workflow nonexistent. |
| **`ARCH-12.2.5`** | Thể tích khối tròn xoay & Quãng đường | `NOT_IMPLEMENTED` | N/A | None | Solid of revolution pipeline nonexistent. |
| **`ARCH-12.3.1`** | Tọa độ vectơ, Tích vô hướng, Tích có hướng 3D | `NOT_IMPLEMENTED` | N/A | None | 3D Vector & cross-product engine nonexistent. |
| **`ARCH-12.3.2`** | Phương trình mặt cầu | `NOT_IMPLEMENTED` | N/A | None | Sphere geometry object nonexistent. |
| **`ARCH-12.3.3`** | Phương trình mặt phẳng | `NOT_IMPLEMENTED` | N/A | None | Plane geometry solver nonexistent. |
| **`ARCH-12.3.4`** | Phương trình đường thẳng trong $Oxyz$ | `NOT_IMPLEMENTED` | N/A | None | 3D Line geometry solver nonexistent. |
| **`ARCH-12.3.5`** | Khoảng cách & Góc trong $Oxyz$ | `NOT_IMPLEMENTED` | N/A | None | 3D metric formula engine nonexistent. |
| **`ARCH-12.4.1`** | Xác suất có điều kiện $P(A\|B)$ | `NOT_IMPLEMENTED` | N/A | None | Conditional probability engine nonexistent. |
| **`ARCH-12.4.2`** | Sơ đồ hình cây xác suất | `NOT_IMPLEMENTED` | N/A | None | Probability tree solver nonexistent. |
| **`ARCH-12.4.3`** | Công thức xác suất toàn phần | `NOT_IMPLEMENTED` | N/A | None | Total probability formula nonexistent. |
| **`ARCH-12.4.4`** | Công thức Bayes | `NOT_IMPLEMENTED` | N/A | None | Bayes theorem solver nonexistent. |
| **`ARCH-12.5.1`** | Khoảng biến thiên & IQR mẫu ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Dispersion for grouped data nonexistent. |
| **`ARCH-12.5.2`** | Phương sai & Độ lệch chuẩn ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Variance for grouped data nonexistent. |
| **`ARCH-12.5.3`** | So sánh mức độ phân tán 2 mẫu ghép nhóm | `NOT_IMPLEMENTED` | N/A | None | Statistical comparison engine nonexistent. |
| **`ARCH-12.E1.1`** | Tích phân ứng dụng vật lý nâng cao | `NOT_IMPLEMENTED` | N/A | None | Applied physics integration nonexistent. |
| **`ARCH-12.E2.1`** | Tọa độ không gian ứng dụng thực tế | `NOT_IMPLEMENTED` | N/A | None | Spatial modeling nonexistent. |
| **`ARCH-12.E3.1`** | Phân bố xác suất nhị thức & chuẩn | `NOT_IMPLEMENTED` | N/A | None | Discrete/continuous distribution engine nonexistent. |

---

## 3. Gap Analysis Synthesis & Root Constraints

1. **Parser Inadequacy for THPT Math:**
   - Current parser handles only polynomials, simple rational fractions, and basic exponents.
   - It cannot parse square roots (`\sqrt{x}`), absolute values (`|x|`), trigonometric functions (`\sin, \cos`), logarithms (`\ln, \log_a`), limits (`\lim`), combinations/permutations ($C_n^k, A_n^k$), or spatial vectors ($\vec{u}, \vec{v}$).
2. **Missing Operation Contracts (`contracts.py`):**
   - Current `OperationType` only includes `SOLVE, SIMPLIFY, DIFFERENTIATE, INTEGRATE, PLOT_2D, SOLVE_SYSTEM, SOLVE_INEQUALITY`.
   - Missing core high-school operations: `LIMIT, ASYMPTOTE, EXTREMA, MONOTONICITY, TANGENT_LINE, AREA_BETWEEN_CURVES, VOLUME_REVOLUTION, VECTOR_CROSS, PLANE_EQUATION, LINE_3D, SPHERE, DESCRIPTIVE_STATS, CONDITIONAL_PROBABILITY, BAYES`.
3. **Absence of Dedicated Mathematical Model Objects:**
   - There are no objects representing Geometric Figures (Lines, Planes, Spheres, Triangles), Statistical Datasets (grouped/ungrouped tables), or Probability Spaces. Everything is forced into a raw symbolic expression string.
