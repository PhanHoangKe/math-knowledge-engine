# MKE PRODUCT-03C — CRITICAL DESIGN CORRECTIONS & MATHEMATICAL RIGOR AUDIT

**Author:** Antigravity (Implementation Engineer)  
**Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Milestone:** PRODUCT-03C-P0  
**Version:** 1.0.0 (Design Baseline Correction)  

---

## 1. Correction of the Rational Equation Example

### Previous Inaccurate Draft Formulation
In preliminary draft notes, the example equation $\frac{x}{x-2} + \frac{1}{x+1} = \frac{6}{x^2-x-2}$ had an errant root calculation claim (stating candidate roots $x=2$ and $x=-2$).

### Rigorous Mathematical Derivation & Correction

Given the rational equation:
$$\frac{x}{x-2} + \frac{1}{x+1} = \frac{6}{x^2 - x - 2}$$

#### Step 1: Exact Domain Determination
Notice that the quadratic denominator factors as:
$$x^2 - x - 2 = (x - 2)(x + 1)$$
The domain of definition requires all denominators to be non-zero:
$$\mathcal{D} = \mathbb{R} \setminus \{ -1, 2 \}$$
Explicit domain restrictions:
$$x \ne -1 \quad \text{and} \quad x \ne 2$$

#### Step 2: Clearing Denominators (under assumption $x \in \mathcal{D}$)
Multiplying both sides by the least common denominator $(x-2)(x+1)$:
$$x(x + 1) + 1(x - 2) = 6$$

#### Step 3: Polynomial Reduction
$$x^2 + x + x - 2 = 6$$
$$x^2 + 2x - 8 = 0$$

#### Step 4: Solving the Reduced Quadratic
Factor the quadratic:
$$(x - 2)(x + 4) = 0$$
Candidate roots from the algebraic reduction:
$$x_1 = 2, \quad x_2 = -4$$

#### Step 5: Candidate Root Screening against Domain $\mathcal{D}$
1. **Candidate $x_1 = 2$:**
   $$\text{Denominator check at } x = 2: \quad (2 - 2) = 0 \implies \text{UNDEFINED}$$
   $x_1 = 2 \notin \mathcal{D} \implies$ **EXTRANEOUS ROOT (Excluded by Domain Violation)**.
2. **Candidate $x_2 = -4$:**
   $$\text{Denominator check at } x = -4: \quad (-4 - 2) = -6 \ne 0, \quad (-4 + 1) = -3 \ne 0$$
   $$\text{Back-substitution check: } \frac{-4}{-6} + \frac{1}{-3} = \frac{2}{3} - \frac{1}{3} = \frac{1}{3}$$
   $$\text{RHS check: } \frac{6}{(-4)^2 - (-4) - 2} = \frac{6}{16 + 4 - 2} = \frac{6}{18} = \frac{1}{3}$$
   $LHS \equiv RHS \implies x_2 = -4 \in \mathcal{D}$ is the **UNIQUE VALID ROOT**.

#### Formal Solution Set:
$$\mathcal{S} = \{ -4 \}$$

---

## 2. Mathematical Refutation of Simplistic Step Equivalence

### The Defective Assumption
In early pedagogical design notes, it was suggested that algebraic step equivalence between consecutive steps $E_k$ and $E_{k+1}$ could be universally validated simply by checking if:
$$\text{LHS}_k - \text{RHS}_k \equiv \text{LHS}_{k+1} - \text{RHS}_{k+1}$$

### Why This Assumption is Mathematically Flawed:

1. **Equation Scaling & Denominator Clearing:**
   - When clearing denominators in $\frac{P(x)}{Q(x)} = 0 \implies P(x) = 0$, the expression value changes by a factor of $Q(x)$:
     $$\left(\frac{P(x)}{Q(x)}\right) - 0 \ne P(x) - 0$$
   - The expressions are NOT identically equal, but the equation solution sets ARE equal on $\mathcal{D} = \{x \mid Q(x) \ne 0\}$.
2. **Non-Invertible Transformations (Squaring & Radical Clearing):**
   - Squaring $\sqrt{f(x)} = g(x) \implies f(x) = [g(x)]^2$ is an implication ($\implies$), not an equivalence ($\iff$).
   - It expands the solution set to include extraneous roots where $g(x) < 0$.
   - Simplistic expression subtraction completely fails to detect this domain expansion.
3. **Linear Combinations in Systems of Equations:**
   - In 2x2 systems, replacing Equation 2 with $a \cdot \text{Eq}_1 + b \cdot \text{Eq}_2$ produces entirely different individual expressions, yet preserves the linear system solution space.

### Correct Mathematical Step Verification Contract
In MKE, an algebraic step must be modeled and verified as a **Guarded State Transition**:
$$\langle E_k, \mathcal{D}_k \rangle \underset{\text{Rule } R}{\overset{\text{Valid}}{\longrightarrow}} \langle E_{k+1}, \mathcal{D}_{k+1} \rangle$$

The step is mathematically verified (`VERIFIED_WITH_EVIDENCE`) if and only if:
1. **Solution Set Preservation:** $\mathcal{S}(E_k) \cap \mathcal{D}_k = \mathcal{S}(E_{k+1}) \cap \mathcal{D}_{k+1}$.
2. **Domain Tracking Invariant:** $\mathcal{D}_{k+1} \subseteq \mathcal{D}_k$, and any newly introduced domain constraints (e.g. $g(x) \ge 0$) are explicitly logged and screened in subsequent verification passes.

---

## 3. Benchmark Dataset Status Correction

### Clarification:
- The preliminary draft mentioning "200 curated algebraic problems published in `tests/benchmarks/`" was a prospective design target, **not an existing published dataset**.
- Furthermore, a 200-item algebra-only dataset is **wholly insufficient** to benchmark the Vietnamese GDPT 2018 High School Mathematics curriculum across Grades 10–12.
- In accordance with the new Project Owner objective, the benchmark strategy is formally replaced by the **300 Diagnostic $\longrightarrow$ 1,000+ Scaled THPT Benchmark Specification** documented in [`docs/curriculum/THPT_BENCHMARK_SPECIFICATION.md`](file:///D:/mke-product-ui-r4/docs/curriculum/THPT_BENCHMARK_SPECIFICATION.md).
