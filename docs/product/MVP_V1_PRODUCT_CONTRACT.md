# MKE MVP V1 — Product Contract & Workspace Specification

- **Document Identifier:** `docs/product/MVP_V1_PRODUCT_CONTRACT.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.1.0 (Remediated Product Contract & Preflight Specification)
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/mvp-v1-product-preflight`
- **Predecessor Baseline:** P1C-04-B2 Accepted (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
- **Parked B3 Baseline:** Parked on `product/p03c-p1c-04-b3-exact-complex-preflight` (`cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`)
- **Status:** `STATUS: PENDING INDEPENDENT MVP PREFLIGHT AUDIT`
- **Date:** 2026-10-01

---

## 1. Executive Vision & Strategic Pivot

### 1.1 The Strategic Pivot
The Math Knowledge Engine (MKE) project is transitioning from a serial solver-capability expansion track (B0 Affine $\to$ B1 Rational Quadratic $\to$ B2 Quadratic Surd $\to$ B3 Complex) toward an integrated, end-to-end mathematical knowledge system.

MKE is fundamentally **NOT a mere answer calculator or black-box solver**. It is a **Vietnam-first, verification-first, interactive mathematical workbench and knowledge graph**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               MKE CONCEPTUAL PIPELINE                                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
  User Input (Text / Math LaTeX / Image)
        │
        ▼
  [Untrusted Multimodal / OCR Ingestion] ──► Produces raw tokens and confidence scores
        │
        ▼
  [Typed MathIR Intake & Semantic Validation] ──► Deterministic syntax & domain guard
        │
        ▼
  [Method Planner & Orthogonal Registry] ──► Multi-dimensional assessment for problem family
        │
        ▼
  [Candidate Generation (Native / CAS)] ──► Untrusted candidate generation
        │
        ▼
  [Independent Verification & Proof Certificates] ──► Strict deterministic host truth gate
        │
        ▼
  [Structured Solution / Proof Traces] ──► Step-by-step verified deduction DAG
        │
        ▼
  [Vietnamese Pedagogical Renderer] ──► Multi-mode presentation (GDPT 2018 aligned)
        │
        ▼
  [Interactive Workbench Frontend] ──► Dynamic editing, recomputation, visualization
```

### 1.2 Mathematical Truth & The AI Boundary Invariant
To guarantee educational integrity and prevent LLM hallucinations, MKE enforces a strict architectural boundary:

> [!IMPORTANT]
> **Core Architectural Invariant:** AI is an assistant for human communication, NEVER the authority on mathematical truth.

| Pipeline Function | AI Role (Permitted) | Deterministic Kernel / Verifier Role (Mandatory) |
| :--- | :--- | :--- |
| **Vietnamese Query Parsing** | Proposes candidate `ProblemIR` and mathematical intent | MKE Intake Validator deterministically validates grammar, bounds, and AST structure |
| **OCR / Image Ingestion** | Transcribes visual math symbols into LaTeX | Schema validator checks mathematical well-formedness; low-confidence triggers confirmation |
| **Method Selection** | Suggests pedagogical hints | Method Registry deterministically evaluates multi-dimensional applicability predicates against problem AST |
| **Solving & Deductions** | Proposes candidate transformations | Independent Host Verifier proves algebraic identities and verifies certificates |
| **Pedagogical Text** | Paraphrases verified steps into student-friendly Vietnamese | Steps must strictly cite deterministic rules, formulas, and verified certificates |

---

## 2. Single Problem Workspace Contract

An active MKE workspace transforms a static problem into a rich, reactive, verified knowledge object.

### 2.1 The 19-Point Workspace Anatomy

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MKE WORKSPACE: QUADRATIC EQUATION WORKBENCH                                         [VERIFIED] [V1]  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. ORIGINAL INPUT:  x^2 - 5*x + 6 = 0                                                                │
│ 2. FORMAL INTERPRETATION: Phương trình bậc hai một ẩn: x² - 5x + 6 = 0, ẩn x ∈ ℝ                     │
│ 3. ASSUMPTIONS & DOMAIN: Hệ số a, b, c ∈ ℚ; a = 1 (a ≠ 0), b = -5, c = 6; Miền nghiệm: x ∈ ℝ         │
│ 4. FINAL ANSWER: x₁ = 2,  x₂ = 3 (Tập nghiệm S = {2; 3})                                             │
│ 5. VERIFICATION STATUS: [✓ VERIFIED COMPLETE] (Chứng chỉ xác thực độc lập: Viète & Khai triển đa thức)│
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. SUPPORTED METHODS IN REGISTRY: [Biệt thức Δ] [Công thức thu gọn] [Phân tích nhân tử]              │
│                                   [Tách bình phương] [Định lý Viète] [Khảo sát đồ thị]               │
│ 7. APPLICABLE METHODS (Orthogonal Multi-Dimensional Assessment):                                     │
│    • Phân tích nhân tử trên ℚ (Tách ac): (x - 2)(x - 3) = 0 [RECOMMENDED, SUPPORTED, AVAILABLE]      │
│    • Công thức nghiệm tổng quát (Δ = 1 > 0): x = (5 ± 1)/2 [RECOMMENDED, SUPPORTED, AVAILABLE]       │
│    • Biến đổi tách bình phương: (x - 5/2)² = 1/4 [NEUTRAL, SUPPORTED, AVAILABLE]                     │
│    • Nhẩm nghiệm theo định lý Viète (S = 5, P = 6 ⇒ x = 2, 3) [RECOMMENDED, SUPPORTED, AVAILABLE]     │
│ 8. NON-APPLICABLE METHODS & REASONS:                                                                 │
│    • Nhẩm nghiệm đặc biệt a + b + c = 0 (1 - 5 + 6 = 2 ≠ 0): [NOT_APPLICABLE: Tổng hệ số khác 0]    │
│    • Nhẩm nghiệm đặc biệt a - b + c = 0 (1 + 5 + 6 = 12 ≠ 0): [NOT_APPLICABLE: Hiệu hệ số khác 0]   │
│    • Công thức thu gọn (b = -5 không là số chẵn): [NOT_APPLICABLE: Hệ số b lẻ]                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 9. VERIFIED STEP-BY-STEP SOLUTION TRACE (Phương pháp chọn: Phân tích nhân tử trên ℚ):                │
│    [Bước 1] Xác định hệ số: a = 1, b = -5, c = 6. Tìm 2 số u, v có u*v = a*c = 6 và u + v = -5: (-2, -3)│
│    [Bước 2] Tách hạng tử giữa: x² - 2x - 3x + 6 = 0                                                  │
│    [Bước 3] Nhóm nhân tử chung: x(x - 2) - 3(x - 2) = 0 ⇔ (x - 2)(x - 3) = 0                        │
│    [Bước 4] Giải phương trình tích: x - 2 = 0 hoặc x - 3 = 0 ⇔ x = 2 hoặc x = 3                      │
│    [Bước 5] Kết luận tập nghiệm trên ℝ: S = {2; 3}                                                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 10. FORMULAS & THEOREMS: [Hằng đẳng thức tích] [Quy tắc giải PT tích A*B = 0] [Định lý Viète]        │
│ 11. PREREQUISITE KNOWLEDGE: [Phép nhân đa thức] [Phân tích đa thức thành nhân tử]                    │
│ 12. QUICK TRICKS & CONDITIONS:                                                                       │
│     • Nhẩm nghiệm tích - tổng: Áp dụng khi a = 1 và S, P là số nguyên có ước số nhỏ.                 │
│ 13. DYNAMIC VISUALIZATION: Đồ thị Parabol y = x² - 5x + 6 (Đỉnh I(2.5, -0.25), Cắt trục Ox tại x=2,3)│
│ 14. RELATED PROBLEM FAMILIES: [Dấu tam thức bậc hai] [Hệ thức Viète và dấu các nghiệm]             │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 15. EDITABLE PARAMETERS: [ a = 1 ] [ b = -5 ] [ c = 6 ]   <-- Người dùng sửa c = 7                   │
│ 16. DEPENDENCY-AWARE RECOMPUTATION: Tự động tính lại Δ = -3, chuyển sang NO_REAL_ROOT, cập nhật đồ thị│
│ 17. METHOD COMPARISON: Bảng so sánh các phương pháp về độ dài bước giải và độ phức tạp tính toán     │
│ 18. PRESENTATION MODES: (•) Học nhanh  ( ) Học hiểu  ( ) So sánh  ( ) Khám phá  ( ) Giáo viên        │
│ 19. SYSTEM HEALTH & TRACEABILITY: Hash xác thực SHA-256, Thời gian tính < 50ms, Bộ nhớ an toàn       │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Precise Definition of "All Methods"
> [!IMPORTANT]
> In MKE, **"All Methods" strictly means all methods currently registered and verified in the MKE Method Registry for that specific problem family**.
> MKE never claims to enumerate "all mathematically conceivable methods" in existence.

---

## 3. Five Learner-Oriented Presentation Modes

The presentation mode alters pedagogical granularity, explanation depth, and layout ordering without ever modifying the verified mathematical facts.

| Mode | Vietnamese Title | Target Audience | Primary Focus | Content Rendered |
| :--- | :--- | :--- | :--- | :--- |
| **Mode 1** | **Học nhanh** | Học sinh ôn thi, cần kết quả và cách giải tối ưu ngắn gọn | Đáp án chính xác, phương pháp tối ưu nhất, các bước giải vắn tắt chuẩn mực | • Kết quả & Verification Badge<br>• 1 lời giải tối ưu chuẩn mực<br>• Công thức mấu chốt |
| **Mode 2** | **Học hiểu** | Học sinh đang học bài mới, cần hiểu bản chất | Giải thích "Tại sao làm bước này?", liên hệ kiến thức nền tảng, minh họa hình học | • Lời giải chi tiết từng bước<br>• Khối "Tại sao làm như vậy?"<br>• Kiến thức tiên quyết (Prerequisites)<br>• Đồ thị trực quan |
| **Mode 3** | **So sánh phương pháp** | Học sinh khá giỏi, luyện tư duy đa chiều | Đặt các phương pháp song song, so sánh ưu/nhược điểm và điều kiện áp dụng | • Bảng so sánh đa cột các phương pháp<br>• Đánh giá độ dài & độ phức tạp<br>• Nhận xét khi nào nên dùng cách nào |
| **Mode 4** | **Khám phá (Interactive)** | Học sinh tự học qua thực nghiệm | Tương tác biến số (slider, input), quan sát đồ thị và nghiệm biến thiên theo thời gian thực | • Bộ điều khiển tham số (Sliders)<br>• Đồ thị động Parabol<br>• Phân tích độ nhạy của nghiệm |
| **Mode 5** | **Giáo viên** | Giáo viên soạn bài, phân tích sư phạm | Khung chuẩn kiến thức GDPT 2018, ma trận phương pháp, bẫy lỗi sai thường gặp của học sinh | • Mã chuẩn CT GDPT 2018 (tham chiếu có thể cấu hình)<br>• Danh sách lỗi sai kinh điển (Common Pitfalls)<br>• Đề bài tương tự và bài toán phát triển |

---

## 4. Algebra MVP Contract: Quadratic Equation Workbench

### 4.1 Input Object & Mathematical Scope
- **Equation Form:** $a x^2 + b x + c = 0$ with exact rational coefficients $a, b, c \in \mathbb{Q}, a \neq 0$.
- **Target Solution Domain:** Real numbers $\mathbb{R}$ for MVP V1 (`solution_domain = "R"`).
- **Semantics of Negative Discriminant ($\Delta < 0$):**
  - In $\mathbb{R}$, $\Delta < 0$ yields the valid mathematical conclusion: **Phương trình vô nghiệm thực** (`solution_type = "NO_REAL_ROOT"`, $S = \emptyset$).
  - This is a complete, successful mathematical solution, NOT an error, NOT unsupported, and does not require complex arithmetic (B3).
- **Curriculum Alignment & Provenance:**
  - *Target Curriculum Profile:* Vietnamese Secondary School Mathematics (Chương trình Giáo dục phổ thông 2018 — GDPT 2018, Thông tư 32/2018/TT-BGDĐT).
  - *Grade 9:* Phương trình bậc hai một ẩn, biệt thức $\Delta$, công thức nghiệm tổng quát và thu gọn, định lý Viète và ứng dụng.
  - *Grade 10:* Tam thức bậc hai, dấu của tam thức bậc hai, đồ thị hàm số bậc hai $y = ax^2 + bx + c$.
  - *Provenance Disclaimer:* Exact GDPT 2018 topic and grade code mappings are maintained in configurable metadata tables and subject to verification against authoritative Ministry of Education and Training (MoET) curriculum documents.

### 4.2 Orthogonal Multi-Dimensional Method Assessment

In MKE, method evaluation does not use a single flat status enum. Instead, every registered method is evaluated along orthogonal dimensions:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 ORTHOGONAL METHOD ASSESSMENT MODEL                                     │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────────────────────┤
│ Dimension                │ Type / Enum Values          │ Semantic Meaning                              │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ `mathematical_applicable`│ `APPLICABLE`                │ Mathematically valid for this problem instance │
│                          │ `NOT_APPLICABLE`            │ Preconditions not satisfied (e.g. Δ < 0, a=0) │
│                          │ `UNKNOWN`                   │ Indeterminate within current engine rules     │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ `support_status`         │ `SUPPORTED`                 │ Fully implemented in MKE solver engine        │
│                          │ `UNSUPPORTED`               │ Defined in ontology but solver unready        │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ `execution_availability` │ `AVAILABLE`                 │ Dependencies ready, executable immediately    │
│                          │ `UNAVAILABLE`               │ Execution worker or resource unavailable      │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ `pedagogical_rec`        │ `RECOMMENDED`               │ Optimal / canonical approach for learners     │
│                          │ `NEUTRAL`                   │ Valid alternative, standard complexity        │
│                          │ `DISCOURAGED`               │ Overly cumbersome for this specific instance  │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ `verification_capability`│ `HOST_VERIFIABLE`           │ Verifiable by deterministic host proof engine │
│                          │ `UNVERIFIED` / `N_A`        │ Not host verified / visual heuristic only     │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────────────────────┘
```

### 4.3 Registered Solution Methods for Quadratic Equations

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   QUADRATIC METHOD REGISTRY (MVP V1)                                   │
├──────────────────────────┬─────────────────────────────┬───────────────────────┬───────────────────────┤
│ Method Identifier        │ Name (Vietnamese)           │ Math Precondition     │ Verification Type     │
├──────────────────────────┼─────────────────────────────┼───────────────────────┼───────────────────────┤
│ `QUAD_FORMULA_STANDARD`  │ Công thức nghiệm tổng quát  │ a ≠ 0                 │ HOST_VERIFIABLE (Alg) │
│ `QUAD_FORMULA_REDUCED`   │ Công thức nghiệm thu gọn    │ a ≠ 0, b = 2b' (b chẵn)│ HOST_VERIFIABLE (Alg) │
│ `QUAD_FACTORIZATION_Q`   │ Phân tích nhân tử trên ℚ    │ Δ là số chính phương ℚ│ HOST_VERIFIABLE (Alg) │
│ `QUAD_FACTORIZATION_R`   │ Phân tích nhân tử trên ℝ    │ Δ ≥ 0                 │ HOST_VERIFIABLE (Alg) │
│ `QUAD_COMPLETE_SQUARE`   │ Biến đổi tách bình phương   │ a ≠ 0                 │ HOST_VERIFIABLE (Alg) │
│ `QUAD_VIETE_SPECIAL_SUM` │ Nhẩm nghiệm a + b + c = 0   │ a + b + c == 0        │ HOST_VERIFIABLE (Alg) │
│ `QUAD_VIETE_SPECIAL_DIF` │ Nhẩm nghiệm a - b + c = 0   │ a - b + c == 0        │ HOST_VERIFIABLE (Alg) │
│ `QUAD_VIETE_SUM_PRODUCT` │ Tìm hai số theo Tổng & Tích │ Δ ≥ 0, S, P hữu tỉ đẹp│ HOST_VERIFIABLE (Alg) │
│ `QUAD_GRAPHICAL_ANALYSIS`│ Khảo sát đồ thị Parabol     │ a ≠ 0                 │ VISUAL_HEURISTIC_ONLY │
└──────────────────────────┴─────────────────────────────┴───────────────────────┴───────────────────────┘
```

#### Detailed Method Specifications & Pedagogical Guardrails

1. **`QUAD_FORMULA_STANDARD` (Công thức nghiệm tổng quát):**
   - *Precondition:* $a \neq 0$. Applicable to **all** quadratic equations with $a, b, c \in \mathbb{Q}$.
   - *Logic:* Compute $\Delta = b^2 - 4ac$.
     - If $\Delta > 0 \implies x_{1,2} = \frac{-b \pm \sqrt{\Delta}}{2a}$ (two distinct real roots).
     - If $\Delta = 0 \implies x_1 = x_2 = \frac{-b}{2a}$ (one repeated real root).
     - If $\Delta < 0 \implies$ Phương trình vô nghiệm trong $\mathbb{R}$ (`NO_REAL_ROOT`).
2. **`QUAD_FORMULA_REDUCED` (Công thức nghiệm thu gọn):**
   - *Precondition:* $a \neq 0$ and $b$ is an even rational number ($b = 2b'$).
   - *Formula:* $\Delta' = (b')^2 - ac$.
   - *Pedagogical Value:* Giảm thiểu khối lượng tính toán khi hệ số bậc nhất chẵn.
3. **`QUAD_FACTORIZATION_Q` vs `QUAD_FACTORIZATION_R` (Phân tích nhân tử):**
   - *Factoring over $\mathbb{Q}$ (`QUAD_FACTORIZATION_Q`):* Precondition is that $\Delta = s^2$ for some $s \in \mathbb{Q}$. Uses $ac$-method to find integers/rationals $u, v$ such that $u+v=b$ and $u \cdot v = ac$, factoring $ax^2+bx+c = (a_1 x + c_1)(a_2 x + c_2) = 0$. Supported for non-monic $a \neq 1$ (e.g. $2x^2+5x+3=(2x+3)(x+1)=0$).
   - *Factoring over $\mathbb{R}$ (`QUAD_FACTORIZATION_R`):* Applicable when $\Delta \ge 0$. Factors as $a(x - x_1)(x - x_2) = 0$ using real surd roots (e.g. $x^2 - 2 = (x - \sqrt{2})(x + \sqrt{2}) = 0$). Explicitly distinguished from rational factoring.
4. **`QUAD_COMPLETE_SQUARE` (Biến đổi tách bình phương):**
   - *Precondition:* $a \neq 0$. Applicable to **all** quadratic equations.
   - *Algorithm:* $a\left(x + \frac{b}{2a}\right)^2 = \frac{\Delta}{4a}$.
   - *Pedagogical Value:* Giúp học sinh hiểu nguồn gốc đại số của công thức nghiệm.
5. **`QUAD_VIETE_SPECIAL_SUM` & `QUAD_VIETE_SPECIAL_DIF` (Nhẩm nghiệm đặc biệt):**
   - *Sum Case ($a + b + c = 0$):* $x_1 = 1, x_2 = \frac{c}{a}$.
   - *Diff Case ($a - b + c = 0$):* $x_1 = -1, x_2 = -\frac{c}{a}$.
   - *Pedagogical Value:* Tối ưu tốc độ giải khi các hệ số có tổng/hiệu đặc biệt.
6. **`QUAD_VIETE_SUM_PRODUCT` (Tìm hai số biết Tổng và Tích):**
   - *Strict Definition:* Định lý Viète ($S = -b/a, P = c/a$) là định lý về mối quan hệ giữa các nghiệm và hệ số. Nó đóng vai trò phương pháp tìm nghiệm độc lập khi người học có thể nhẩm hoặc phân tích được hai số có tổng $S$ và tích $P$. MKE không coi Viète là thuật toán giải vạn năng cho mọi nghiệm vô tỉ phức tạp.
7. **`QUAD_GRAPHICAL_ANALYSIS` (Khảo sát đồ thị Parabol):**
   - *Invariant:* Parabol $y = ax^2+bx+c$ là công cụ trực quan hóa hình học, hỗ trợ hiểu bản chất giao điểm với trục hoành, **KHÔNG PHẢI là chứng chỉ chứng minh đại số độc lập**.

---

## 5. Interactive Mutation & Dependency Invalidation Scenarios

When a user edits any parameter in the workspace, MKE executes a dependency-aware DAG invalidation and selective recomputation.

### 5.1 Concrete Mutation Walkthrough: $x^2 - 5x + 6 = 0 \longrightarrow x^2 - 5x + 7 = 0$

```
[Initial State: a=1, b=-5, c=6]                  [User Action: Edit c from 6 to 7]
  • Δ = (-5)² - 4(1)(6) = 1 > 0                     • c := 7
  • Δ is square (1 = 1²)                            • Parameter Hash updated: H_old -> H_new
  • Roots: x₁ = 2, x₂ = 3                           │
  • Factorization: (x-2)(x-3)=0 [APPLICABLE]        ▼
  • Viète Guessing: S=5, P=6 [APPLICABLE]   [DAG Invalidation Triggered]
  • Graph: Vertex I(2.5, -0.25), Cuts Ox            │
                                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ DEPENDENCY RECOMPUTATION CASCADE (c = 7)                                                             │
├──────────────────────────┬──────────────────────┬────────────────────────────────────────────────────┤
│ Artifact Node            │ Recomputed Value     │ Invalidation & Transition Outcome                  │
├──────────────────────────┼──────────────────────┼────────────────────────────────────────────────────┤
│ `DiscriminantNode`       │ Δ = 25 - 28 = -3 < 0 │ Đổi dấu từ dương sang âm (Δ > 0 → Δ < 0)          │
│ `RootClassification`    │ `NO_REAL_ROOT`       │ Tập nghiệm rỗng trong ℝ (S = ∅)                    │
│ `RootsValueNode`         │ `[]` (Empty list)    │ Hủy các nghiệm x₁=2, x₂=3                          │
│ `FactorizationMethod_Q`  │ `NOT_APPLICABLE`     │ Không phân tích được nhân tử hữu tỉ (Δ < 0)        │
│ `VieteGuessingMethod`    │ `NOT_APPLICABLE`     │ Không có 2 số thực có tổng 5 và tích 7             │
│ `GeneralFormulaTrace`    │ `Recomputed`         │ Tạo trace kết luận vô nghiệm vì Δ = -3 < 0         │
│ `GraphVisualization`     │ `Parabol Lifted`     │ Đỉnh mới I(2.5, +0.75) nằm hoàn toàn phía trên Ox  │
│ `PedagogicalAdvice`      │ `Updated`            │ Gợi ý: "Parabol không cắt trục hoành, Δ < 0"       │
│ `VerificationCertificate`│ `Re-certified`       │ Host chứng minh a > 0 và Δ < 0 ⇒ ax²+bx+c > 0, ∀x │
└──────────────────────────┴──────────────────────┴────────────────────────────────────────────────────┘
```

### 5.2 Generic Parameterized Family Evaluation
- **MVP V1 Cut Line:** Parameter exploration in MVP V1 is **numeric parameter mutation** ($a, b, c \in \mathbb{Q}$ edited via sliders or numeric inputs).
- **Post-V1 Extension:** Purely symbolic parameter analysis (e.g., "Tìm $m$ để phương trình $x^2 - 2mx + m^2 - 1 = 0$ có hai nghiệm phân biệt") requires algebraic constraint inequality solvers and is designated for **MVP V2**.

---

## 6. Linear Systems Cut-Line Decision

### 6.1 Systems of First-Degree Equations Evaluation ($2 \times 2$ Linear Systems)
$$\begin{cases} a_1 x + b_1 y = c_1 \\ a_2 x + b_2 y = c_2 \end{cases}$$

Candidate Solution Methods:
1. Phương pháp cộng đại số (Elimination)
2. Phương pháp thế (Substitution)
3. Phương pháp hình học (Giao điểm hai đường thẳng trên mặt phẳng $Oxy$)
4. Quy tắc Cramer (Định thức $D, D_x, D_y$) — *Lưu ý sư phạm: Cramer thuộc chuyên đề nâng cao Lớp 10, không phải trọng tâm cơ bản Lớp 9*.

### 6.2 Architectural Recommendation: CUT LINE = MVP V1B
> [!NOTE]
> **Decision: Schedule Linear Systems for MVP V1B.**
> 
> *Rationale:*
> 1. Quadratic Equation Workbench is rich enough to establish all core product pillars (multi-method registry, step-by-step verified traces, interactive parameter recomputation, dynamic parabola graphing, and presentation modes).
> 2. Keeping V1 focused strictly on **1D Quadratic Algebra** + **2D Triangle Geometry** prevents architectural surface bloat while proving the multi-domain knowledge engine model.

---

## 7. Geometry MVP Contract: Triangle Geometry Workbench

### 7.1 Vision: Dynamic Geometry with Verified Proof Traces
MKE Geometry Workbench treats geometric figures not as static images, but as **semantically declared theorem environments**.

> [!CAUTION]
> **The Geometry Proof Invariant:**
> A diagram is **NOT** a proof. Coordinate agreement on screen is **NOT** a synthetic deduction.
> Dragging a point in the UI updates the coordinate realization of the scene, while the underlying mathematical proof relies strictly on semantic geometric axioms and deductive inference rules.
> Coordinates are used only for **counterexample / falsification filtering**, never as a proof certificate.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ GEOMETRY WORKBENCH: TAM GIÁC VÀ ĐƯỜNG ĐẶC BIỆT                                           │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ĐỀ BÀI: Cho tam giác ABC cân tại A. Gọi M là trung điểm của BC. Chứng minh AM ⊥ BC.      │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ KHAI BÁO NGỮ NGHĨA (GeometryProblemIR):                                                  │
│   • Primitives: NonDegenerateTriangle(A, B, C), Midpoint(M, BC), Segment(AM)             │
│   • Givens: EqualLength(AB, AC), Midpoint(M, BC)                                         │
│   • Goal: Perpendicular(AM, BC)                                                         │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ CÁC PHƯƠNG PHÁP CHỨNG MINH ĐƯỢC HỖ TRỢ:                                                  │
│   [Cách 1: Tam giác bằng nhau (c-c-c)] [Cách 2: Tính chất tam giác cân]                  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ CHỨNG MINH XÁC THỰC (Cách 1: ΔABM = ΔACM):                                              │
│   1. Xét ΔABM và ΔACM có:                                                                │
│      - AB = AC (giả thiết tam giác ABC cân tại A)                                        │
│      - MB = MC (M là trung điểm BC theo giả thiết)                                       │
│      - AM là cạnh chung                                                                  │
│   2. Suy ra ΔABM = ΔACM (c-c-c) [RULE_TRIANGLE_CONGRUENCE_SSS].                          │
│   3. Suy ra ∠AMB = ∠AMC (hai góc tương ứng).                                             │
│   4. Mà ∠AMB + ∠AMC = 180° (hai góc kề bù) ⇒ ∠AMB = ∠AMC = 90°.                          │
│   5. Vậy AM ⊥ BC (điều phải chứng minh). [✓ VERIFIED DEDUCTIVE PROOF]                    │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ HÌNH VẼ ĐỘNG (JSXGraph):                                                                 │
│   • Điểm A có thể kéo rê trên đường trung trực của BC mà vẫn giữ tính chất tam giác cân. │
│   • Khi kéo B hoặc C, điểm M tự động bám theo trung điểm.                                │
│   • Nếu kéo A, B, C thẳng hàng: Canvas chuyển sang trạng thái cảnh báo DEGENERATE.       │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Geometry MVP Cut-Line Decisions

| Capability | In Scope for MVP V1? | Decision & Justification |
| :--- | :--- | :--- |
| **Tam giác không suy biến & Quan hệ cạnh/góc** | **YES (Core V1)** | Nền tảng hình học THCS (Lớp 7–8 GDPT 2018). Ba điểm không thẳng hàng ($\text{Area} > 0$). |
| **3 Đường đặc biệt cơ bản** (Trung tuyến, Đường cao, Phân giác) | **YES (Core V1)** | Đủ để minh họa đa phương pháp chứng minh (tam giác bằng nhau, tính chất đối xứng). |
| **Đường tròn ngoại tiếp (Circumcircle)** | **NO (Deferred to V1B)** | Cần mở rộng thêm kiểu hình học đường tròn, góc nội tiếp, tứ giác nội tiếp. |
| **Các tâm tam giác cơ bản** (Trọng tâm G, Trực tâm H) | **Trọng tâm G & Trực tâm H (V1 Minimal)** | Cung cấp bài toán giao điểm 3 đường đặc biệt. Tâm nội tiếp, tâm bàng tiếp hoãn lại. |
| **Free Auxiliary-Line Construction** (Kẻ đường phụ tự do) | **NO (Template-Guided in V1, Free in V2)** | Kẻ đường phụ tự do yêu cầu không gian tìm kiếm chứng minh vô hạn; V1 hỗ trợ các đường phụ được định nghĩa theo mẫu bài toán. |

---

## 8. Summary of Product States

```
┌─────────────────────────┬────────────────────────────────────────────────────────────────────┐
│ Product State           │ Meaning & User Feedback                                            │
├─────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ `VERIFIED`              │ Đã giải và xác thực 100% bằng chứng chỉ toán học độc lập.          │
│ `PARTIALLY_VERIFIED`    │ Một số bước tính được chứng minh, một số bước dựa trên heuristic.   │
│ `NO_PROOF_FOUND`        │ Hệ thống không tìm được chứng minh trong hệ luật hỗ trợ hiện tại.   │
│ `UNSUPPORTED`           │ Bài toán nằm ngoài phạm vi tri thức hiện tại của MKE.               │
│ `AMBIGUOUS_INPUT`       │ Đề bài mơ hồ, thiếu giả thiết (MKE yêu cầu người dùng làm rõ).     │
│ `INVALID_INPUT`         │ Đề bài sai cú pháp toán học hoặc vi phạm miền (ví dụ: a = 0).       │
│ `DEGENERATE_STATE`      │ Cấu hình hình học suy biến (ví dụ: 3 đỉnh tam giác thẳng hàng).    │
│ `RESOURCE_LIMIT`        │ Kích thước bài toán vượt quá giới hạn tài nguyên an toàn.          │
│ `INTERNAL_ERROR`        │ Lỗi hệ thống nội bộ (được ghi log cách ly).                        │
└─────────────────────────┴────────────────────────────────────────────────────────────────────┘
```
