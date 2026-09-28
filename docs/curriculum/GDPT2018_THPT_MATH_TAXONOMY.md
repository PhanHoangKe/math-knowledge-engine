# GDPT 2018 THPT MATHEMATICS CURRICULUM TAXONOMY
## Comprehensive Hierarchy & Problem Archetypes (Grades 10–12)

**Author:** Antigravity (Implementation Engineer)  
**Curriculum Standard:** Chương trình Giáo dục Phổ thông 2018 — Môn Toán (Ban hành kèm Thông tư số 32/2018/TT-BGDĐT)  
**Scope:** Core Mandatory Curriculum, Elective Modules (Chuyên đề học tập), and Enrichment Boundaries  
**Version:** 1.0.0 (Design Baseline)  

---

## 1. Taxonomy Structural Schema

Each curriculum unit is classified into the following 5-level hierarchy:
$$\text{Grade} \longrightarrow \text{Strand} \longrightarrow \text{Topic} \longrightarrow \text{Required Competency} \longrightarrow \text{Problem Archetype}$$

### Curriculum Category Flags:
- `[CORE]`: Mandatory core curriculum assessed in National High School Graduation Exams (Kỳ thi Tốt nghiệp THPT).
- `[ELECTIVE]`: Elective specialized modules (Chuyên đề học tập nâng cao theo định hướng nghề nghiệp).
- `[OLYMPIAD]`: Competitive enrichment (Học sinh giỏi / Olympic), strictly distinguished from secondary school graduation core.

---

## 2. Grade 10 Mathematics (Lớp 10)

### Strand 1: Đại số và Một số yếu tố Giải tích (Algebra & Elementary Analysis)

#### Topic 10.1: Mệnh đề và Tập hợp (Mathematical Logic & Sets) `[CORE]`
- **Required Competencies:**
  - Xác định chân trị mệnh đề, mệnh đề phủ định, mệnh đề kéo theo, mệnh đề tương đương, mệnh đề chứa ký hiệu $\forall, \exists$.
  - Thực hiện các phép toán tập hợp: giao ($A \cap B$), hợp ($A \cup B$), hiệu ($A \setminus B$), phần bù ($C_E A$) trên các tập con của $\mathbb{R}$ (khoảng, đoạn, nửa khoảng).
- **Problem Archetypes:**
  - `ARCH-10.1.1`: Xét tính đúng/sai của mệnh đề logic và mệnh đề phủ định chứa $\forall, \exists$.
  - `ARCH-10.1.2`: Tìm tập hợp giao, hợp, hiệu của hai tập hợp số dạng khoảng, đoạn (e.g. $(-3; 5] \cap (2; 7)$).
  - `ARCH-10.1.3`: Tìm tham số $m$ để phép toán tập hợp thỏa mãn điều kiện (e.g. $A \cap B = \emptyset$).

#### Topic 10.2: Bất phương trình và Hệ bất phương trình bậc nhất hai ẩn (Linear Inequalities & Systems in 2 Variables) `[CORE]`
- **Required Competencies:**
  - Biểu diễn miền nghiệm của bất phương trình bậc nhất hai ẩn $ax + by \le c$ trên mặt phẳng tọa độ $Oxy$.
  - Xác định miền nghiệm của hệ bất phương trình bậc nhất hai ẩn (miền đa giác lồi).
  - Giải bài toán tối ưu tuyến tính quy hoạch thực tế: Tìm giá trị lớn nhất / nhỏ nhất của biểu thức $F(x, y) = ax + by$ trên miền đa giác.
- **Problem Archetypes:**
  - `ARCH-10.2.1`: Kiểm tra điểm $(x_0, y_0)$ thuộc hoặc không thuộc miền nghiệm của bất phương trình/hệ bất phương trình.
  - `ARCH-10.2.2`: Xác định đỉnh của miền đa giác nghiệm từ hệ bất phương trình.
  - `ARCH-10.2.3`: Tối ưu hóa hàm mục tiêu $F(x, y) = ax + by$ trên miền nghiệm (Linear Programming).

#### Topic 10.3: Hàm số bậc hai và Đồ thị (Quadratic Functions & Graphs) `[CORE]`
- **Required Competencies:**
  - Khảo sát sự biến thiên, vẽ parabol $y = ax^2 + bx + c$ ($a \ne 0$), xác định tọa độ đỉnh $I(-b/2a; -\Delta/4a)$, trục đối xứng, khoảng đồng biến/nghịch biến.
  - Tìm tập xác định, tập giá trị, giá trị lớn nhất/nhỏ nhất của hàm bậc hai trên một đoạn $[p; q]$.
- **Problem Archetypes:**
  - `ARCH-10.3.1`: Xác định tọa độ đỉnh, trục đối xứng và bảng biến thiên của parabol.
  - `ARCH-10.3.2`: Tìm hàm số bậc hai $y = ax^2 + bx + c$ đi qua 3 điểm hoặc biết đỉnh và 1 điểm.
  - `ARCH-10.3.3`: Tìm Min/Max của hàm bậc hai trên đoạn kín $[p; q]$.

#### Topic 10.4: Dấu của tam thức bậc hai & Bất phương trình bậc hai một ẩn `[CORE]`
- **Required Competencies:**
  - Xét dấu của tam thức bậc hai $f(x) = ax^2 + bx + c$ dựa vào dấu của $a$ và $\Delta$.
  - Giải bất phương trình bậc hai một ẩn $ax^2 + bx + c > 0, \ge 0, < 0, \le 0$.
  - Tìm điều kiện tham số $m$ để tam thức bậc hai giữ nguyên dấu trên $\mathbb{R}$ hoặc trên một khoảng.
- **Problem Archetypes:**
  - `ARCH-10.4.1`: Giải bất phương trình bậc hai $ax^2 + bx + c \gtrless 0$.
  - `ARCH-10.4.2`: Tìm $m$ để tam thức bậc hai $f(x) > 0, \forall x \in \mathbb{R}$ (hệ $a > 0, \Delta < 0$).
  - `ARCH-10.4.3`: Giải bất phương trình tích/thương chứa các nhân tử bậc nhất và bậc hai.

#### Topic 10.5: Phương trình quy về phương trình bậc hai `[CORE]`
- **Required Competencies:**
  - Giải phương trình chứa căn dạng căn bản: $\sqrt{ax^2 + bx + c} = \sqrt{dx^2 + ex + f}$ và $\sqrt{ax^2 + bx + c} = dx + e$.
  - Kiểm tra điều kiện xác định và loại nghiệm ngoại lai (extraneous roots).
- **Problem Archetypes:**
  - `ARCH-10.5.1`: Giải phương trình $\sqrt{f(x)} = \sqrt{g(x)}$ (bình phương hai vế có điều kiện).
  - `ARCH-10.5.2`: Giải phương trình $\sqrt{ax^2 + bx + c} = dx + e$ (điều kiện $dx + e \ge 0$).
  - `ARCH-10.5.3`: Giải phương trình chứa dấu giá trị tuyệt đối $|ax + b| = cx + d$ và $|ax + b| = |cx + d|$.

#### Topic 10.6: Đại số tổ hợp (Combinatorics & Binomial Expansion) `[CORE]`
- **Required Competencies:**
  - Áp dụng quy tắc cộng, quy tắc nhân, sơ đồ hình cây.
  - Tính số hoán vị $P_n = n!$, chỉnh hợp $A_n^k = \frac{n!}{(n-k)!}$, tổ hợp $C_n^k = \frac{n!}{k!(n-k)!}$.
  - Khai triển nhị thức Newton $(a + b)^n$ với số mũ $n \in \{4, 5\}$.
- **Problem Archetypes:**
  - `ARCH-10.6.1`: Tính giá trị tổ hợp, chỉnh hợp, giải phương trình/bất phương trình chứa $A_n^k, C_n^k$.
  - `ARCH-10.6.2`: Đếm số phương án chọn đối tượng thỏa mãn điều kiện chia hết, vị trí, chữ số.
  - `ARCH-10.6.3`: Khai triển $(ax + b)^4, (ax + b)^5$ và tìm hệ số của số hạng $x^k$.

---

### Strand 2: Hình học và Đo lường (Geometry & Trigonometry in 2D)

#### Topic 10.7: Hệ thức lượng trong tam giác (Trigonometric Relations in Triangles) `[CORE]`
- **Required Competencies:**
  - Giá trị lượng giác của góc từ $0^\circ$ đến $180^\circ$.
  - Định lí côsin: $a^2 = b^2 + c^2 - 2bc \cos A$.
  - Định lí sin: $\frac{a}{\sin A} = \frac{b}{\sin B} = \frac{c}{\sin C} = 2R$.
  - Các công thức tính diện tích tam giác: $S = \frac{1}{2}ab \sin C = \frac{abc}{4R} = pr = \sqrt{p(p-a)(p-b)(p-c)}$.
- **Problem Archetypes:**
  - `ARCH-10.7.1`: Tính góc, cạnh, bán kính $R, r$ của tam giác khi biết trước 3 yếu tố.
  - `ARCH-10.7.2`: Tính diện tích tam giác bằng công thức Heron hoặc sin.
  - `ARCH-10.7.3`: Bài toán thực tế đo chiều cao tháp, khoảng cách giữa hai điểm không tới được.

#### Topic 10.8: Vectơ trong mặt phẳng (Vectors in 2D) `[CORE]`
- **Required Competencies:**
  - Các phép toán vectơ: tổng, hiệu, tích vectơ với một số.
  - Biểu diễn một vectơ theo hai vectơ không cùng phương.
  - Tích vô hướng của hai vectơ: $\vec{a} \cdot \vec{b} = |\vec{a}| |\vec{b}| \cos(\vec{a}, \vec{b})$, tính góc giữa hai vectơ, chứng minh hai vectơ vuông góc.
- **Problem Archetypes:**
  - `ARCH-10.8.1`: Biểu diễn vectơ $\vec{u}$ theo hai vectơ cơ sở $\vec{a}, \vec{b}$.
  - `ARCH-10.8.2`: Tính tích vô hướng $\vec{a} \cdot \vec{b}$ và độ dài đoạn thẳng trong hình phẳng.
  - `ARCH-10.8.3`: Tính góc giữa hai vectơ và chứng minh tính vuông góc $\vec{a} \cdot \vec{b} = 0$.

#### Topic 10.9: Phương pháp tọa độ trong mặt phẳng Oxy (2D Coordinate Geometry) `[CORE]`
- **Required Competencies:**
  - Tọa độ vectơ, tọa độ điểm, trung điểm, trọng tâm, tích vô hướng trong tọa độ.
  - Phương trình đường thẳng: tổng quát $ax + by + c = 0$, tham số $\begin{cases}x = x_0 + at \\ y = y_0 + bt\end{cases}$, chính tắc.
  - Vị trí tương đối giữa hai đường thẳng, góc giữa hai đường thẳng, khoảng cách từ điểm đến đường thẳng.
  - Phương trình đường tròn $(x-a)^2 + (y-b)^2 = R^2$, phương trình tiếp tuyến của đường tròn.
  - Ba đường Conic: Elip $\frac{x^2}{a^2} + \frac{y^2}{b^2} = 1$, Hypebol $\frac{x^2}{a^2} - \frac{y^2}{b^2} = 1$, Parabol $y^2 = 2px$.
- **Problem Archetypes:**
  - `ARCH-10.9.1`: Viết phương trình đường thẳng qua điểm biết VTCP/VTPT, qua 2 điểm, song song/vuông góc đường thẳng cho trước.
  - `ARCH-10.9.2`: Tính khoảng cách từ điểm đến đường thẳng; tính góc giữa 2 đường thẳng.
  - `ARCH-10.9.3`: Viết phương trình đường tròn biết tâm/bán kính, qua 3 điểm; viết phương trình tiếp tuyến.
  - `ARCH-10.9.4`: Xác định các yếu tố tiêu cự, đỉnh, tiêu điểm, tâm sai của Elip, Hypebol, Parabol.

---

### Strand 3: Thống kê và Xác suất (Statistics & Classical Probability)

#### Topic 10.10: Thống kê mô tả (Descriptive Statistics for Ungrouped Data) `[CORE]`
- **Required Competencies:**
  - Số đặc trưng đo xu thế trung tâm: Số trung bình ($\bar{x}$), Trung vị ($M_e$), Mốt ($M_o$), Tứ phân vị ($Q_1, Q_2, Q_3$).
  - Số đặc trưng đo mức độ phân tán: Khoảng biến thiên ($R$), Khoảng tứ phân vị ($\Delta_Q = Q_3 - Q_1$), Giá trị ngoại lệ (outlier), Phương sai ($s^2$), Độ lệch chuẩn ($s$).
- **Problem Archetypes:**
  - `ARCH-10.10.1`: Tính số trung bình, trung vị, tứ phân vị của mẫu số liệu không ghép nhóm.
  - `ARCH-10.10.2`: Tính khoảng biến thiên, khoảng tứ phân vị, tìm giá trị ngoại lệ.
  - `ARCH-10.10.3`: Tính phương sai và độ lệch chuẩn của bảng số liệu.

#### Topic 10.11: Xác suất cổ điển (Classical Probability) `[CORE]`
- **Required Competencies:**
  - Không gian mẫu ($\Omega$), biến cố, biến cố đối ($\bar{A}$), biến cố hợp, biến cố giao.
  - Tính xác suất theo định nghĩa cổ điển: $P(A) = \frac{n(A)}{n(\Omega)}$.
  - Quy tắc cộng xác suất cho biến cố xung khắc: $P(A \cup B) = P(A) + P(B)$.
- **Problem Archetypes:**
  - `ARCH-10.11.1`: Liệt kê và tính số phần tử của không gian mẫu trong phép thử chọn ngẫu nhiên.
  - `ARCH-10.11.2`: Tính xác suất biến cố bằng tổ hợp và quy tắc đếm.
  - `ARCH-10.11.3`: Tính xác suất biến cố đối $P(\bar{A}) = 1 - P(A)$.

---

### Grade 10 Chuyên đề học tập (Elective Modules) `[ELECTIVE]`
- `ARCH-10.E1.1`: Giải hệ phương trình bậc nhất 3 ẩn bằng phương pháp khử Gauss.
- `ARCH-10.E1.2`: Chứng minh đẳng thức/bất đẳng thức bằng phương pháp Quy nạp toán học.
- `ARCH-10.E1.3`: Khai triển nhị thức Newton $(a+b)^n$ với $n$ bất kỳ và tìm hệ số lớn nhất.
- `ARCH-10.E2.1`: Ứng dụng ba đường conic vào bài toán quỹ đạo thiên văn và gương phản xạ.

---

## 3. Grade 11 Mathematics (Lớp 11)

### Strand 1: Đại số và Một số yếu tố Giải tích (Trigonometry, Sequences & Calculus)

#### Topic 11.1: Hàm số lượng giác và Phương trình lượng giác (Trigonometric Functions & Equations) `[CORE]`
- **Required Competencies:**
  - Đơn vị đo góc radian, công thức lượng giác cơ bản, công thức cộng, nhân đôi, biến đổi tích thành tổng, tổng thành tích.
  - Khảo sát tập xác định, tính chẵn/lẻ, chu kì, đồ thị của các hàm số $y = \sin x, \cos x, \tan x, \cot x$.
  - Giải phương trình lượng giác cơ bản: $\sin x = m, \cos x = m, \tan x = m, \cot x = m$.
  - Giải phương trình bậc hai đối với một hàm số lượng giác và phương trình bậc nhất đối với $\sin x$ và $\cos x$ ($a\sin x + b\cos x = c$).
- **Problem Archetypes:**
  - `ARCH-11.1.1`: Tính giá trị biểu thức lượng giác và rút gọn biểu thức bằng công thức cộng/nhân đôi.
  - `ARCH-11.1.2`: Tìm tập xác định và chu kì tuần hoàn của hàm số lượng giác.
  - `ARCH-11.1.3`: Giải phương trình lượng giác cơ bản $\sin(ax+b) = \sin(cx+d)$, $\cos(ax+b) = m$.
  - `ARCH-11.1.4`: Giải phương trình dạng $a\sin x + b\cos x = c$ và đếm số nghiệm trên khoảng $[p; q]$.

#### Topic 11.2: Dãy số, Cấp số cộng, Cấp số nhân (Sequences, AP & GP) `[CORE]`
- **Required Competencies:**
  - Dãy số: công thức số hạng tổng quát $u_n$, tính tăng/giảm, bị chặn.
  - Cấp số cộng: định nghĩa, số hạng tổng quát $u_n = u_1 + (n-1)d$, tổng $n$ số hạng đầu $S_n = \frac{n(u_1 + u_n)}{2} = \frac{n[2u_1 + (n-1)d]}{2}$.
  - Cấp số nhân: định nghĩa, số hạng tổng quát $u_n = u_1 \cdot q^{n-1}$, tổng $S_n = \frac{u_1(1-q^n)}{1-q}$ ($q \ne 1$).
- **Problem Archetypes:**
  - `ARCH-11.2.1`: Tìm số hạng tổng quát $u_n$ và xét tính tăng/giảm, bị chặn của dãy số.
  - `ARCH-11.2.2`: Tìm $u_1, d$ của cấp số cộng khi biết hệ điều kiện; tính tổng $n$ số hạng đầu $S_n$.
  - `ARCH-11.2.3`: Tìm $u_1, q$ của cấp số nhân; tính tổng $S_n$; tính tổng cấp số nhân lùi vô hạn $S = \frac{u_1}{1-q}$ ($|q| < 1$).
  - `ARCH-11.2.4`: Bài toán thực tế lãi kép, tăng trưởng dân số, phân rã phóng xạ theo cấp số.

#### Topic 11.3: Giới hạn và Hàm số liên tục (Limits & Continuity) `[CORE]`
- **Required Competencies:**
  - Giới hạn dãy số: $\lim \frac{P(n)}{Q(n)}$, $\lim (\sqrt{f(n)} - \sqrt{g(n)})$, $\lim q^n$.
  - Giới hạn hàm số tại một điểm $\lim_{x \to x_0} f(x)$ và tại vô cực $\lim_{x \to \pm\infty} f(x)$, giới hạn một bên $\lim_{x \to x_0^+} f(x), \lim_{x \to x_0^-} f(x)$.
  - Khử các dạng vô định: $\left[\frac{0}{0}\right], \left[\frac{\infty}{\infty}\right], [\infty - \infty], [0 \cdot \infty]$.
  - Khảo sát tính liên tục của hàm số tại một điểm và trên một khoảng; định lí giá trị trung gian (chứng minh phương trình có nghiệm).
- **Problem Archetypes:**
  - `ARCH-11.3.1`: Tính giới hạn dãy số hữu tỉ và căn thức vô định.
  - `ARCH-11.3.2`: Tính giới hạn hàm số dạng vô định $\left[\frac{0}{0}\right]$ bằng phân tích nhân tử hoặc nhân liên hợp.
  - `ARCH-11.3.3`: Tính giới hạn một bên và tìm tham số $m$ để hàm số liên tục tại $x = x_0$.
  - `ARCH-11.3.4`: Chứng minh phương trình $f(x) = 0$ có ít nhất một nghiệm trên $(a; b)$ nhờ tính liên tục.

#### Topic 11.4: Hàm số Mũ và Hàm số Logarit (Exponential & Logarithmic Functions) `[CORE]`
- **Required Competencies:**
  - Phép tính lũy thừa với số mũ thực, tính chất logarit, công thức đổi cơ số $\log_a b = \frac{\log_c b}{\log_c a}$.
  - Tập xác định, tập giá trị, tính đơn điệu và đồ thị hàm số mũ $y = a^x$ và hàm số logarit $y = \log_a x$ ($a > 0, a \ne 1$).
  - Giải phương trình, bất phương trình mũ cơ bản và đưa về cùng cơ số: $a^{f(x)} = a^{g(x)}$, $a^{f(x)} > b$.
  - Giải phương trình, bất phương trình logarit: $\log_a f(x) = \log_a g(x)$, $\log_a f(x) > b$ (với điều kiện xác định nghiêm ngặt).
- **Problem Archetypes:**
  - `ARCH-11.4.1`: Rút gọn và tính giá trị biểu thức chứa lũy thừa, căn thức, logarit.
  - `ARCH-11.4.2`: Tìm tập xác định của hàm số chứa logarit $\log_a [f(x)]$ và lũy thừa $f(x)^\alpha$.
  - `ARCH-11.4.3`: Giải phương trình mũ/logarit cơ bản và bằng phương pháp đặt ẩn phụ $t = a^x$ hoặc $t = \log_a x$.
  - `ARCH-11.4.4`: Giải bất phương trình mũ/logarit có chú ý tính đồng biến/nghịch biến theo cơ số $a$.

#### Topic 11.5: Đạo hàm (Derivatives) `[CORE]`
- **Required Competencies:**
  - Định nghĩa đạo hàm bằng giới hạn, ý nghĩa hình học (hệ số góc tiếp tuyến $k = f'(x_0)$), ý nghĩa vật lý (vận tốc tức thời $v(t) = s'(t)$).
  - Quy tắc tính đạo hàm: tổng, hiệu, tích, thương, đạo hàm hàm hợp $y = f(u(x)) \implies y' = f'(u) \cdot u'(x)$.
  - Đạo hàm các hàm số sơ cấp cơ bản: lũy thừa ($x^\alpha$), căn thức ($\sqrt{x}$), lượng giác ($\sin x, \cos x, \tan x, \cot x$), mũ ($e^x, a^x$), logarit ($\ln x, \log_a x$).
  - Viết phương trình tiếp tuyến của đồ thị hàm số tại điểm $M(x_0; y_0)$ hoặc biết hệ số góc tiếp tuyến $k$.
  - Đạo hàm cấp hai $f''(x)$ và gia tốc tức thời $a(t) = s''(t)$.
- **Problem Archetypes:**
  - `ARCH-11.5.1`: Tính đạo hàm của hàm đa thức, phân thức hữu tỉ, căn thức và lượng giác/mũ/logarit.
  - `ARCH-11.5.2`: Viết phương trình tiếp tuyến của đồ thị hàm số tại điểm thuộc đồ thị có hoành độ $x_0$.
  - `ARCH-11.5.3`: Viết phương trình tiếp tuyến biết tiếp tuyến song song hoặc vuông góc với đường thẳng cho trước.
  - `ARCH-11.5.4`: Tính đạo hàm cấp hai và giải bài toán vận tốc/gia tốc trong vật lý.

---

### Strand 2: Hình học không gian (Spatial Geometry in 3D)

#### Topic 11.6: Quan hệ song song trong không gian (Parallelism in Space) `[CORE]`
- **Required Competencies:**
  - Điểm, đường thẳng, mặt phẳng trong không gian; các tiên đề hình học không gian.
  - Vị trí tương đối: hai đường thẳng song song/chéo nhau; đường thẳng song song mặt phẳng; hai mặt phẳng song song.
  - Phép chiếu song song, hình biểu diễn của các hình không gian.
- **Problem Archetypes:**
  - `ARCH-11.6.1`: Tìm giao tuyến của hai mặt phẳng và giao điểm của đường thẳng với mặt phẳng.
  - `ARCH-11.6.2`: Chứng minh đường thẳng song song với mặt phẳng ($d \parallel (\alpha)$) hoặc hai mặt phẳng song song.
  - `ARCH-11.6.3`: Xác định thiết diện của hình chóp/hình lăng trụ cắt bởi mặt phẳng song song.

#### Topic 11.7: Quan hệ vuông góc trong không gian & Góc, Khoảng cách (Perpendicularity, Angles & Distances in Space) `[CORE]`
- **Required Competencies:**
  - Hai đường thẳng vuông góc; đường thẳng vuông góc với mặt phẳng ($d \perp (\alpha)$); hai mặt phẳng vuông góc.
  - Định lí ba đường vuông góc; phép chiếu vuông góc.
  - Góc giữa hai đường thẳng; góc giữa đường thẳng và mặt phẳng; góc phẳng nhị diện (góc giữa hai mặt phẳng).
  - Khoảng cách từ một điểm đến một đường thẳng/mặt phẳng; khoảng cách giữa hai đường thẳng song song / chéo nhau; thể tích khối chóp, lăng trụ.
- **Problem Archetypes:**
  - `ARCH-11.7.1`: Chứng minh đường thẳng vuông góc mặt phẳng ($d \perp (\alpha)$) và mặt phẳng vuông góc mặt phẳng.
  - `ARCH-11.7.2`: Tính góc giữa đường thẳng và mặt phẳng (góc giữa $d$ và hình chiếu $d'$).
  - `ARCH-11.7.3`: Tính góc phẳng nhị diện giữa hai mặt bên hoặc mặt bên và mặt đáy của hình chóp.
  - `ARCH-11.7.4`: Tính khoảng cách từ chân đường cao đến mặt bên của hình chóp; tính khoảng cách giữa hai đường thẳng chéo nhau.

---

### Strand 3: Thống kê và Xác suất (Grouped Data Statistics & Conditional Probability)

#### Topic 11.8: Thống kê mô tả cho mẫu số liệu ghép nhóm (Descriptive Statistics for Grouped Data) `[CORE]`
- **Required Competencies:**
  - Bảng tần số ghép nhóm; tính số trung bình cộng của mẫu ghép nhóm $\bar{x} = \frac{1}{n} \sum m_i c_i$.
  - Tính trung vị $M_e = u_m + \frac{\frac{n}{2} - C}{n_m} \cdot h$.
  - Tính tứ phân vị $Q_1, Q_2, Q_3$ và mốt $M_o$ của mẫu số liệu ghép nhóm.
- **Problem Archetypes:**
  - `ARCH-11.8.1`: Lập bảng tần số ghép nhóm và tính số trung bình.
  - `ARCH-11.8.2`: Tính trung vị và các tứ phân vị $Q_1, Q_3$ của mẫu số liệu ghép nhóm.
  - `ARCH-11.8.3`: Tính mốt $M_o$ và giải thích ý nghĩa thực tế của các số đặc trưng.

#### Topic 11.9: Các quy tắc tính xác suất cơ bản (Probability Rules & Independent Events) `[CORE]`
- **Required Competencies:**
  - Biến cố độc lập: Hai biến cố $A, B$ độc lập $\iff P(A \cap B) = P(A) \cdot P(B)$.
  - Công thức nhân xác suất cho biến cố độc lập.
  - Công thức cộng xác suất tổng quát: $P(A \cup B) = P(A) + P(B) - P(A \cap B)$.
- **Problem Archetypes:**
  - `ARCH-11.9.1`: Xác định tính độc lập của hai biến cố.
  - `ARCH-11.9.2`: Tính xác suất của biến cố giao $P(A \cap B)$ và biến cố hợp $P(A \cup B)$.
  - `ARCH-11.9.3`: Bài toán thực tế bắn bia, hệ thống linh kiện hoạt động độc lập.

---

### Grade 11 Chuyên đề học tập (Elective Modules) `[ELECTIVE]`
- `ARCH-11.E1.1`: Phép biến hình trong mặt phẳng (Phép tịnh tiến, phép quay, phép vị tự, phép đồng dạng).
- `ARCH-11.E2.1`: Bài toán tài chính thực tế (Tính lãi đơn, lãi kép liên tục, giá trị hiện tại của dòng tiền, bài toán trả góp).
- `ARCH-11.E3.1`: Lý thuyết đồ thị cơ bản (Đồ thị phẳng, bậc của đỉnh, chu trình Euler/Hamilton).

---

## 4. Grade 12 Mathematics (Lớp 12)

### Strand 1: Giải tích nâng cao (Advanced Calculus & Curve Sketching)

#### Topic 12.1: Ứng dụng Đạo hàm để khảo sát và vẽ đồ thị hàm số (Applications of Derivatives & Curve Sketching) `[CORE]`
- **Required Competencies:**
  - Tính đơn điệu: Định lí điều kiện cần và đủ ($f'(x) \ge 0 \implies$ đồng biến).
  - Cực trị hàm số: Điểm cực đại, điểm cực tiểu, định lí dấu hiệu 1 và dấu hiệu 2.
  - Giá trị lớn nhất và giá trị nhỏ nhất của hàm số trên một đoạn $[a; b]$ hoặc trên một khoảng.
  - Đường tiệm cận của đồ thị hàm số: Tiệm cận đứng ($x = x_0$), Tiệm cận ngang ($y = y_0$), Tiệm cận xiên ($y = ax + b$).
  - Khảo sát và vẽ đồ thị các hàm số cơ bản:
    1. Hàm bậc ba: $y = ax^3 + bx^2 + cx + d$ ($a \ne 0$).
    2. Hàm phân thức bậc nhất / bậc nhất: $y = \frac{ax + b}{cx + d}$ ($c \ne 0, ad - bc \ne 0$).
    3. Hàm phân thức bậc hai / bậc nhất: $y = \frac{ax^2 + bx + c}{px + q}$ ($a \ne 0, p \ne 0$).
  - Đọc đồ thị, bảng biến thiên; bài toán tương giao $f(x) = m$; bài toán tối ưu thực tế (cắt góc làm hộp, chi phí tối thiểu).
- **Problem Archetypes:**
  - `ARCH-12.1.1`: Xét tính đơn điệu và tìm cực trị của hàm số từ công thức, đạo hàm $f'(x)$, hoặc bảng biến thiên.
  - `ARCH-12.1.2`: Tìm giá trị lớn nhất, nhỏ nhất của hàm số trên đoạn $[a; b]$.
  - `ARCH-12.1.3`: Tìm số đường tiệm cận đứng, ngang, xiên của đồ thị hàm phân thức hoặc hàm chứa căn.
  - `ARCH-12.1.4`: Nhận dạng hàm số từ đồ thị cho trước (xác định dấu hệ số $a, b, c, d$).
  - `ARCH-12.1.5`: Tìm tham số $m$ để hàm số đơn điệu trên khoảng $(p; q)$ hoặc có $k$ điểm cực trị.
  - `ARCH-12.1.6`: Bài toán tối ưu hóa hình học/kinh tế thực tế ứng dụng đạo hàm.

#### Topic 12.2: Nguyên hàm và Tích phân (Antiderivatives & Integrals) `[CORE]`
- **Required Competencies:**
  - Khái niệm nguyên hàm, bảng nguyên hàm cơ bản và mở rộng ($e^{ax+b}, \frac{1}{ax+b}, \cos(ax+b)$, v.v.).
  - Các phương pháp tìm nguyên hàm: Đổi biến số $t = u(x)$, Từng phần $\int u \, dv = uv - \int v \, du$.
  - Khái niệm tích phân xác định $\int_a^b f(x) \, dx = F(b) - F(a)$, các tính chất của tích phân.
  - Các phương pháp tính tích phân: Đổi biến số, Từng phần.
  - Ứng dụng tích phân tính diện tích hình phẳng giới hạn bởi các đường $y = f(x), y = g(x), x=a, x=b$.
  - Ứng dụng tích phân tính thể tích khối tròn xoay quay quanh trục $Ox$: $V = \pi \int_a^b [f(x)]^2 \, dx$.
- **Problem Archetypes:**
  - `ARCH-12.2.1`: Tìm nguyên hàm của hàm đa thức, phân thức hữu tỉ, lượng giác, mũ bằng bảng công thức.
  - `ARCH-12.2.2`: Tính nguyên hàm/tích phân bằng phương pháp đổi biến số $t = u(x)$.
  - `ARCH-12.2.3`: Tính nguyên hàm/tích phân bằng phương pháp từng phần $\int u \, dv$.
  - `ARCH-12.2.4`: Tính diện tích hình phẳng giới hạn bởi hai đồ thị hàm số.
  - `ARCH-12.2.5`: Tính thể tích khối tròn xoay và giải bài toán vật lý tính quãng đường $s = \int v(t) \, dt$, công $A = \int F(x) \, dx$.

---

### Strand 2: Hình học tọa độ trong không gian Oxyz (Spatial Coordinate Geometry in 3D)

#### Topic 12.3: Tọa độ Vectơ và Phương trình trong không gian Oxyz `[CORE]`
- **Required Competencies:**
  - Hệ tọa độ $Oxyz$, tọa độ điểm, tọa độ vectơ, các phép toán vectơ, tích có hướng của hai vectơ $[\vec{a}, \vec{b}]$.
  - Phương trình mặt cầu $(x-a)^2 + (y-b)^2 + (z-c)^2 = R^2$ hoặc $x^2 + y^2 + z^2 - 2ax - 2by - 2cz + d = 0$.
  - Phương trình mặt phẳng: VTPT, phương trình tổng quát $Ax + By + Cz + D = 0$.
  - Phương trình đường thẳng: VTCP, phương trình tham số $\begin{cases}x = x_0 + at \\ y = y_0 + bt \\ z = z_0 + ct\end{cases}$, chính tắc $\frac{x-x_0}{a} = \frac{y-y_0}{b} = \frac{z-z_0}{c}$.
  - Khoảng cách từ điểm đến mặt phẳng; góc giữa hai mặt phẳng, giữa đường thẳng và mặt phẳng, giữa hai đường thẳng.
  - Vị trí tương đối giữa hai đường thẳng (cắt nhau, song song, trùng nhau, chéo nhau), giữa đường thẳng và mặt phẳng, giữa mặt cầu và mặt phẳng.
- **Problem Archetypes:**
  - `ARCH-12.3.1`: Tính tọa độ vectơ, tích vô hướng, tích có hướng $[\vec{a}, \vec{b}]$, tính diện tích tam giác và thể tích tứ diện trong không gian.
  - `ARCH-12.3.2`: Viết phương trình mặt cầu biết tâm/bán kính, đường kính, qua 4 điểm; xét vị trí tương đối với mặt phẳng.
  - `ARCH-12.3.3`: Viết phương trình mặt phẳng qua 1 điểm biết VTPT, qua 3 điểm, qua 1 điểm và chứa đường thẳng, song song/vuông góc mặt phẳng.
  - `ARCH-12.3.4`: Viết phương trình đường thẳng qua điểm biết VTCP, giao tuyến của 2 mặt phẳng, đường vuông góc chung của 2 đường thẳng chéo nhau.
  - `ARCH-12.3.5`: Tính khoảng cách và góc trong không gian $Oxyz$; tìm hình chiếu vuông góc của điểm lên mặt phẳng/đường thẳng.

---

### Strand 3: Thống kê và Xác suất nâng cao (Advanced Statistics & Probability)

#### Topic 12.4: Xác suất có điều kiện và Công thức Xác suất toàn phần, Công thức Bayes `[CORE]`
- **Required Competencies:**
  - Xác suất có điều kiện: $P(A|B) = \frac{P(A \cap B)}{P(B)}$ ($P(B) > 0$).
  - Sơ đồ hình cây tính xác suất có điều kiện.
  - Công thức xác suất toàn phần: Với hệ biến cố đầy đủ $\{B_1, B_2, \dots, B_n\}$, $P(A) = \sum_{i=1}^n P(B_i) P(A|B_i)$.
  - Công thức Bayes: $P(B_k|A) = \frac{P(B_k) P(A|B_k)}{\sum_{i=1}^n P(B_i) P(A|B_i)}$.
- **Problem Archetypes:**
  - `ARCH-12.4.1`: Tính xác suất có điều kiện $P(A|B)$ từ bảng số liệu hoặc định nghĩa.
  - `ARCH-12.4.2`: Vẽ sơ đồ hình cây và tính xác suất biến cố trong các bài toán nhiều giai đoạn.
  - `ARCH-12.4.3`: Ứng dụng công thức xác suất toàn phần trong bài toán xét nghiệm y tế, kiểm tra chất lượng sản phẩm.
  - `ARCH-12.4.4`: Ứng dụng công thức Bayes để tính xác suất hậu nghiệm (e.g. xác suất thực sự mắc bệnh khi kết quả dương tính).

#### Topic 12.5: Thống kê đo mức độ phân tán cho mẫu ghép nhóm `[CORE]`
- **Required Competencies:**
  - Khoảng biến thiên $R$ và khoảng tứ phân vị $\Delta_Q = Q_3 - Q_1$ của mẫu ghép nhóm.
  - Phương sai $s^2 = \frac{1}{n} \sum m_i c_i^2 - (\bar{x})^2$ và độ lệch chuẩn $s = \sqrt{s^2}$ của mẫu ghép nhóm.
- **Problem Archetypes:**
  - `ARCH-12.5.1`: Tính khoảng biến thiên và khoảng tứ phân vị của mẫu số liệu ghép nhóm.
  - `ARCH-12.5.2`: Tính phương sai và độ lệch chuẩn của mẫu ghép nhóm.
  - `ARCH-12.5.3`: So sánh mức độ phân tán/đồng đều của hai tập dữ liệu ghép nhóm.

---

### Grade 12 Chuyên đề học tập (Elective Modules) `[ELECTIVE]`
- `ARCH-12.E1.1`: Ứng dụng tích phân trong bài toán vật lý (Tính áp lực chất lỏng, trọng tâm vật thể).
- `ARCH-12.E2.1`: Vận dụng phương pháp tọa độ không gian giải bài toán thực tế quy hoạch không gian 3D.
- `ARCH-12.E3.1`: Mô hình hóa xác suất với phân bố nhị thức và phân bố chuẩn.

---

## 5. Summary Taxonomy Statistics

| Grade | Total Core Topics | Core Archetypes | Elective Archetypes | Total Mapped Problem Archetypes |
| :--- | :---: | :---: | :---: | :---: |
| **Grade 10** | 11 | 35 | 4 | **39** |
| **Grade 11** | 9 | 33 | 3 | **36** |
| **Grade 12** | 5 | 24 | 3 | **27** |
| **Total THPT (10–12)** | **25 Topics** | **92 Core Archetypes** | **10 Elective Archetypes** | **102 Archetypes** |
