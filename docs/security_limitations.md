# Tài Liệu Giới Hạn Bảo Mật & Phòng Chống Tấn Công (DEV-01)

Tài liệu này trình bày các cơ chế bảo mật đã triển khai, các giới hạn đã biết và các nguy cơ tiềm ẩn trong kiến trúc tính toán đại số của **Math Knowledge Engine**.

---

## 1. Cơ Chế Bảo Mật Đã Triển Khai

### 1.1. Cách Ly Hoàn Toàn Khỏi Code Execution Động
- **Tuyệt đối cấm**: `eval()`, `exec()`, `compile()`.
- **Cấm SymPy Dynamic Parsing**: Không sử dụng `sympy.sympify(str)` hay `sympy.parsing.sympy_parser.parse_expr(str)` trên chuỗi đầu vào chưa kiểm soát. Các hàm này bên dưới vẫn sử dụng Python AST và `eval()`, dễ bị khai thác tấn công Arbitrary Code Execution (RCE).
- **Cơ chế chuyển đổi an toàn**:
  Chuỗi đầu vào $\to$ Bộ quét từ vựng whitelist (`Lexer`) $\to$ Bộ phân tích cú pháp đệ quy (`Parser`) $\to$ AST tùy biến (`ASTNode`) $\to$ Khởi tạo đối tượng SymPy thông qua các constructor tường minh được cho phép (`sympy.Integer`, `sympy.Rational`, `sympy.Symbol('x')`, `sympy.Add`, `sympy.Mul`, `sympy.Pow`).

### 1.2. Giới Hạn Tài Nguyên Ngăn Chặn Từ Chối Dịch Vụ (DoS / Resource Exhaustion)
Hệ thống thiết lập các ngưỡng chặn cứng (`ParserLimits`) trước khi thực hiện bất kỳ phép toán đại số nào:

| Tham số | Giá trị mặc định | Mục đích ngăn chặn |
|---|---|---|
| `max_input_length` | 300 ký tự | Chống tràn bộ nhớ đệm và ReDoS chuỗi đầu vào |
| `max_tokens` | 150 token | Chống tấn công tạo chuỗi token khổng lồ |
| `max_ast_depth` | 15 cấp | Chống tràn ngăn xếp đệ quy (Recursion Bomb / Stack Overflow) |
| `max_node_count` | 250 node | Giới hạn kích thước cây cú pháp trung gian |
| `max_coefficient_magnitude` | $10^9$ | Chống số nguyên lớn vô hạn làm tê liệt ALU |
| `max_exponent` | 4 | Giới hạn số mũ của đa thức trong phạm vi giải được |
| `max_polynomial_degree` | 4 | Chống bùng nổ tổ hợp trong phân tích đa thức |

---

## 2. Giới Hạn Kỹ Thuật & Rủi Ro Tiềm Ẩn Chưa Xử Lý Hoàn Toàn

1. **Giới hạn về ngắt toán tử SymPy (Timeout Limitation)**:
   - Một số thuật toán phân tích đa thức hoặc giải hệ của thư viện đại số tính toán (như Gröbner bases hay factorization đặc biệt) có thể tiêu tốn CPU đáng kể.
   - Cơ chế timeout dựa trên Thread (`threading.Thread`) trong Python không thể ngắt cưỡng bức mã nguồn C/C++ mở rộng hoặc vòng lặp nội tại đang chạy trong tiến trình mà không gây bất ổn định cho Python interpreter.
   - *Biện pháp hiện tại*: Sử dụng các giới hạn cấu trúc (bậc tối đa 4, hệ số $\le 10^9$) để triệt tiêu bài toán có độ phức tạp cao ngay từ tầng AST trước khi SymPy xử lý.
2. **Ký Tự Mã Hóa Console Trên Môi Trường Windows**:
   - Trên một số phiên bản Windows cũ với code page mặc định không phải UTF-8 (ví dụ cp1258, cp437), việc xuất các ký tự Unicode đồ họa có thể gây `UnicodeEncodeError`. Hệ thống đã chuyển đổi toàn bộ thông báo CLI sang ký tự chuẩn ASCII tương thích (`[PASS]`, `[FAIL]`, `[OK]`).
3. **Phạm Vi Giới Hạn**:
   - Chưa hỗ trợ xử lý đa tiến trình song song (multiprocessing worker pool). Nếu có nhu cầu chịu tải cao, cần bọc pipeline trong tiến trình con độc lập với cơ chế process kill cứng.
