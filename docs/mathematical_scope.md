# Phạm Vi Toán Học & Giới Hạn Nghiên Cứu (DEV-01)

Tài liệu này xác định rõ ranh giới toán học, tiền đề đại số và các giới hạn kỹ thuật của hệ thống **Math Knowledge Engine** trong giai đoạn DEV-01.

---

## 1. Miền Toán Học Được Hỗ Trợ (Supported Mathematical Scope)

### 1.1. Tập Hợp Số và Biến Số
- **Biến số**: Duy nhất một biến thực $x \in \mathbb{R}$. Mọi biến số khác ($y, z, t, \dots$) hoặc phương trình nhiều biến đều bị từ chối an toàn với trạng thái `OUT_OF_SCOPE`.
- **Hệ số và hằng số**: Thuộc trường số hữu tỉ $\mathbb{Q}$ hoặc số nguyên $\mathbb{Z}$. Hằng số thực vô tỉ biểu diễn dạng ký hiệu (như $\pi, e$) hoặc số phức ($i$) không thuộc phạm vi xử lý của DEV-01.

### 1.2. Biểu Thức và Toán Tử Cho Phép
- Phép cộng ($+$), trừ ($-$), nhân ($*$), chia ($/$).
- Phép lũy thừa ($^\wedge$ hoặc $**$) với số mũ là **số nguyên không âm** $n \in \{0, 1, 2, 3, 4\}$.
- Dấu ngoặc đơn $(, )$ xác định thứ tự ưu tiên tính toán.
- Dấu bằng ($=$) phân tách vế trái (LHS) và vế phải (RHS).

### 1.3. Lớp Phương Trình
1. **Phương trình đa thức bậc $\le 4$**:
   - Bậc 0: Phương trình hằng số suy biến ($0 = 0$ đồng nhất thức, $c = 0$ vô nghiệm).
   - Bậc 1: Tuyến tính $a x + b = 0$.
   - Bậc 2: Bậc hai $a x^2 + b x + c = 0$.
   - Bậc 4: Trùng phương $a x^4 + b x^2 + c = 0$ (không chứa bậc lẻ $x^3, x$).
2. **Phương trình phân thức hữu tỉ**:
   - Dạng $\frac{P(x)}{Q(x)} = 0$ hoặc $\frac{P_1(x)}{Q_1(x)} = \frac{P_2(x)}{Q_2(x)}$ trong đó $P, Q$ là các đa thức thuộc phạm vi bậc $\le 4$.
   - Điều kiện xác định mẫu số $Q(x) \neq 0$ bắt buộc được trích xuất từ cây cú pháp (AST) ban đầu trước mọi thao tác rút gọn.

---

## 2. Nguyên Tắc Bảo Toàn Miền Xác Định (Original Domain Preservation)

Trong đại số máy tính truyền thống, việc tự động rút gọn biểu thức có thể làm thay đổi miền xác định của phương trình ban đầu.
Ví dụ điển hình:
$$\frac{x - 2}{x - 2} = 1$$
Nếu rút gọn vế trái trực tiếp bằng $\frac{x-2}{x-2} \to 1$, phương trình trở thành $1 = 1$, dẫn đến kết luận sai lầm rằng tập nghiệm là toàn bộ $\mathbb{R}$.

**Quy tắc bất biến của Math Knowledge Engine:**
1. Miền xác định $\text{Domain} = \mathbb{R} \setminus \{x_0 \mid Q(x_0) = 0\}$ được trích xuất trực tiếp từ **AST chưa rút gọn (unreduced AST)**.
2. Không bao giờ dựa vào biểu thức đã chuẩn hóa/rút gọn để suy ngược lại miền xác định.
3. Khi phương trình tương đương với $0 = 0$, tập nghiệm được kết luận là:
   $$\mathcal{S} = \text{OriginalDomain} = \mathbb{R} \setminus \{2\}$$
4. Mọi nghiệm ứng viên thu được từ việc giải tử số $P(x) = 0$ sau khi khử mẫu đều phải được thẩm định lại qua nghĩa vụ chứng minh `ORIGINAL_DOMAIN`. Nếu $Q(r) = 0$, nghiệm $r$ bị loại bỏ và ghi nhận là nghiệm ngoại lai (*extraneous root*).

---

## 3. Danh Mục Phương Pháp (Method Catalogue)

Hệ thống triển khai 5 phương pháp nền tảng với định danh ổn định:

| Method ID | Tên Phương Pháp | Dạng Chuẩn | Điều Kiện Áp Dụng (Guards) | Nghĩa Vụ Chứng Minh Chính |
|---|---|---|---|---|
| `M1:LINEAR_EQUATION` | Giải phương trình bậc nhất | $ax + b = 0$ | Bậc $\le 1$, phi phân thức | $a \neq 0$ (`NONZERO_GUARD`), nhánh suy biến (`PARAMETER_BRANCH`) |
| `M2:QUADRATIC_FORMULA` | Công thức nghiệm bậc hai | $ax^2 + bx + c = 0$ | Bậc $= 2$, phi phân thức, $a \neq 0$ | $a \neq 0$, phân loại $\Delta \ge 0$ vs $\Delta < 0$, tính đầy đủ |
| `M3:FACTORIZATION` | Phân tích nhân tử | $\prod F_i(x) = 0$ | Bậc $\ge 2$, phân tích được trên $\mathbb{Q}$ | Bảo toàn nghiệm, không chia cho biểu thức chứa $x$ |
| `M4:RATIONAL_EQUATION` | Phương trình phân thức | $\frac{P(x)}{Q(x)} = 0$ | Chứa phân thức đại số | Khử mẫu an toàn, loại nghiệm ngoại lai (`ORIGINAL_DOMAIN`) |
| `M5:BIQUADRATIC_SUBSTITUTION` | Đặt ẩn phụ trùng phương | $ax^4 + bx^2 + c = 0$ | Bậc 4, khuyết bậc lẻ, $a \neq 0$ | Ràng buộc dấu $t = x^2 \ge 0$ (`SIGN_CONSTRAINT`), khôi phục $x = \pm\sqrt{t}$ |

---

## 4. Những Dạng Toán NẰM NGOÀI PHẠM VI (Out-of-Scope)

Hệ thống từ chối an toàn các dạng đầu vào sau và trả về `OUT_OF_SCOPE`:
- Phương trình chứa căn thức: $\sqrt{x+2} = x$, $\sqrt[3]{x} = 1$.
- Hàm số lượng giác: $\sin(x), \cos(x), \tan(x), \cot(x)$.
- Hàm siêu việt: $\ln(x), \log(x), e^x, \exp(x)$.
- Hàm trị tuyệt đối: $|x|$.
- Bất phương trình: $x^2 - 4 > 0$, $x \le 3$.
- Đa thức bậc $> 4$ (ví dụ: $x^5 - x + 1 = 0$).
- Phương trình nhiều biến hoặc hệ phương trình.

Nếu một bài toán nằm ngoài khả năng chứng minh đầy đủ, hệ thống trả về nhãn `UNRESOLVED` hoặc `UNDETERMINED`, tuyệt đối không đoán nhận kết quả.
