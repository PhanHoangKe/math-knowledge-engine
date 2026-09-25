# BÁO CÁO KỸ THUẬT VÀ NGHIỆM THU KIỂM TOÁN ĐỘC LẬP
## DEV-01-R3-S2 — FINITE FINAL TRUST-BOUNDARY PATCH
**Dự án:** Math Knowledge Engine (MKE)  
**Nhiệm vụ:** DEV-01-R3-S2  
**Kỹ sư thực hiện:** Senior Mathematical Verification & Research Reproducibility Engineer  
**Ngày thực hiện:** 25/09/2026  
**Nhánh Git:** `dev01-r3-s2-patch` (phân nhánh từ `dev01-r3-s1-patch` tại commit `a3ee264`)  

---

### 1. TỔNG QUAN VÀ BỐI CẢNH

Sau đợt chuyển giao DEV-01-R3-S1, người điều phối kiểm toán độc lập đã thực hiện khảo sát biên sâu và phát hiện hai lỗ hổng ranh giới tin cậy (trust-boundary gaps) trong báo cáo `DATN_DEV01_R3_S1_INDEPENDENT_AUDIT_2026-09-25.md`:
1. **F5 — Inexact values certified as exact:** Giá trị xấp xỉ dấu phẩy động `sympy.Float('1.0', 15)` nhận chứng chỉ `EXACT_PASS` đối với phương trình $x - (1 + 10^{-30}) = 0$ do giới hạn độ chính xác số học máy làm phép trừ triệt tiêu thành `0.0` (trong SymPy `0.0 == 0` là `True`).
2. **F6 — Certificate includes unverified submitted roots:** Hàm kiểm toán độc lập `audit_independent_completeness` khi nhận danh sách nghiệm hỗn hợp (chứa cả nghiệm đúng và giá trị sai/vô nghĩa như `['1', '2']` hoặc `['1', 'not_a_root']` cho $x - 1 = 0$) đã âm thầm loại bỏ phần tử lỗi khỏi tập đối sánh nội bộ nhưng vẫn cấp chứng chỉ `PASS` và giữ nguyên các phần tử lỗi trong thuộc tính `cert.verified_roots`.

Nhiệm vụ DEV-01-R3-S2 được thực hiện với phạm vi kiểm soát nghiêm ngặt: khắc phục triệt để hai lỗ hổng F5 và F6, bảo toàn toàn bộ 129 bài kiểm thử nội bộ và các bộ cổng kiểm toán độc lập tiền nhiệm (R2, R3), không mở rộng tính năng hay chuyển sang DEV-02.

---

### 2. TÁI HIỆN LỖ HỔNG TRƯỚC KHI SỬA ĐỔI MÃ NGUỒN

Trước khi can thiệp vào mã nguồn sản xuất, bộ kiểm thử độc lập nguyên trạng `DATN_DEV01_R3_S1_INDEPENDENT_EDGE_GATES.py` đã được chạy trên nhánh `dev01-r3-s2-patch` (kế thừa mã nguồn DEV-01-R3-S1). Kết quả ghi nhận chính xác 3 ca thất bại:
- `test_f5_inexact_sympy_float_must_not_get_exact_certificate`: **FAILED** (Giá trị `sp.Float('1.0', 15)` được chứng nhận `EXACT_PASS` cho $x - (1 + 10^{-30}) = 0$).
- `test_f6_mixed_correct_and_incorrect_root_cannot_pass`: **FAILED** (Batch `['1', '2']` cho $x - 1 = 0$ trả về `status = PASS` và `verified_roots = ['1', '2']`).
- `test_f6_mixed_correct_and_malformed_root_cannot_pass`: **FAILED** (Batch `['1', 'not_a_root']` cho $x - 1 = 0$ trả về `status = PASS` và `verified_roots = ['1', 'not_a_root']`).

---

### 3. NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE ANALYSIS)

#### 3.1. Nguyên nhân gốc rễ F5:
- Trong `verify_root_exact` (`src/mke/models/domain.py`), phép thay thế `raw_sub = expr.subs(var, sym_r)` với `sym_r = sp.Float('1.0', 15)` cho kết quả `0.0`. Do câu lệnh kiểm tra `if raw_sub == 0: return EXACT_PASS`, Python/SymPy đánh giá `0.0 == 0` là `True`, dẫn tới việc cấp chứng chỉ chính xác tuyệt đối cho một nghiệm xấp xỉ không đúng.
- Mã nguồn còn tồn tại nhánh chuyển đổi thụ động `elif isinstance(r, float): sym_r = Rational(Fraction(str(r)))`, cố gắng "đoán" số hữu tỉ từ biểu diễn thập phân làm mờ ranh giới nguồn gốc (provenance) giữa giá trị ký hiệu giải tích chính xác và số thực tính toán dấu phẩy động.

#### 3.2. Nguyên nhân gốc rễ F6:
- Trong `audit_independent_completeness` (`src/mke/verification/completeness.py`), danh sách ứng viên đầu vào được lọc vào tập `parsed_verified`. Những ứng viên sai hoặc không hợp lệ bị bỏ qua mà không đánh dấu cờ lỗi (`has_rejected`).
- Thuộc tính `cert.verified_roots` được gán trực tiếp bằng toàn bộ danh sách chuỗi đầu vào thô (`verified_roots_str_list`).
- Khi tập `parsed_verified` vô tình trùng khớp với nghiệm chính tắc (ví dụ `{1} == {1}`), hệ thống kết luận `can_pass = True`, cấp chứng chỉ `PASS` trong khi vẫn bảo chứng cho cả các giá trị sai như `2` hay `not_a_root`.

---

### 4. BIỆN PHÁP KHẮC PHỤC KỸ THUẬT (REMEDIATIONS)

#### 4.1. Khắc phục F5 (Chính sách ranh giới chính xác tuyệt đối & cấm Float):
1. **Xây dựng hàm kiểm định nguồn gốc số học `contains_inexact_float(obj: Any) -> bool`** tại `src/mke/models/domain.py`:
   - Kiểm tra chặt chẽ kiểu `float`, `sympy.Float`, hoặc bất kỳ biểu thức `sympy.Basic` nào chứa nguyên tử `sympy.Float` hoặc `float` (`obj.has(sympy.Float)` và duyệt `atoms()`).
2. **Fail-closed tại cổng kiểm chứng `verify_root_exact`**:
   - Nếu biểu thức `expr` hoặc nghiệm ứng viên `r` chứa `Float`, trả về ngay chứng chỉ `ExactProofCertificate` với trạng thái `status = UNRESOLVED`, `is_exact_pass = False`, `method = "INEXACT_FLOAT_UNSUPPORTED"`.
   - Loại bỏ hoàn toàn khối ép kiểu thụ động từ `float` sang `Fraction(str(r))`.
   - Kiểm tra phòng thủ bổ sung đối với kết quả thế `raw_sub`: nếu `raw_sub` xuất hiện `Float`, lập tức từ chối `EXACT_PASS`.
3. **Áp dụng đồng bộ chính sách cấm Float trên toàn hệ thống**:
   - `check_root_satisfaction`: Trả về `(False, sympy.nan)` nếu `contains_inexact_float` là True.
   - `OriginalDomain.contains`: Trả về `False` ngay lập tức nếu giá trị kiểm tra hoặc giá trị loại trừ chứa `Float`.
   - `safe_parse_candidate_root` & `audit_solution_transfer` (`src/mke/verification/transfer.py`): Từ chối và ném lỗi/phân loại vào `rejected_roots`, phân loại `TransferValidity.UNSAFE_COPY`.
   - `_roots_match`: Từ chối khớp đại số nếu một trong hai tập chứa phần tử `Float`.

#### 4.2. Khắc phục F6 (Kế toán ứng viên toàn vẹn & chứng chỉ không chứa nghiệm rác):
1. **Phân loại toàn bộ ứng viên đầu vào thành hai luồng độc lập**:
   - `valid_verified_roots_sym` & `valid_verified_roots_str`: Chỉ chứa các giá trị thực sự hợp lệ, thuộc miền xác định $D$ và vượt qua `verify_root_exact` với `EXACT_PASS`.
   - `rejected_candidates_str`: Ghi nhận tất cả các ứng viên bị lỗi cú pháp, vi phạm miền xác định, dư lượng khác 0, chứa số thực xấp xỉ `Float`, hoặc chứng chỉ giả mạo.
2. **Nguyên tắc chặn chứng nhận `PASS`**:
   - Cờ lỗi `has_rejected = len(rejected_candidates_str) > 0`.
   - Điều kiện đạt chứng chỉ: `can_pass = (not has_rejected) and (len(all_extraneous) == 0) and _roots_match(canonical_domain_roots, valid_verified_roots_sym)`.
   - Nếu tồn tại bất kỳ ứng viên nào bị từ chối, chứng chỉ tuyệt đối **KHÔNG** nhận `PASS` (trả về `FAIL` hoặc `UNRESOLVED`).
3. **Bảo đảm tính trung thực của chứng chỉ**:
   - `cert.verified_roots = dedup_valid_str`: **CHỈ** chứa các nghiệm đã được chứng minh hợp lệ. Tuyệt đối không bao giờ chứng nhận nghiệm rác.
   - `cert.extraneous_roots = rejected_candidates_str + unmatched_valid`: Liệt kê minh bạch tất cả các ứng viên không hợp lệ hoặc thừa.
   - `cert.details["rejected_candidates"] = rejected_candidates_str`: Lưu vết chi tiết lý do từ chối.
4. **Áp dụng nhất quán trên tất cả các phân nhánh phương trình**:
   - Bậc 1 (Linear), Bậc 2 (Quadratic), Bậc 4 Trùng phương (Biquadratic), Phân tích nhân tử hữu tỉ (Factored), Bậc cao vô nghiệm thực (Sturm Isolation Empty), Phương trình mâu thuẫn (Contradiction), Miền rỗng (Empty Domain).

---

### 5. KẾT QUẢ KIỂM THỬ THỰC TẾ

Tất cả các bộ kiểm thử đều được thực thi trực tiếp trên môi trường máy chủ với kết quả trung thực:

| Bộ kiểm thử | Mục đích | Số lượng test | Kết quả | Ghi chú |
| :--- | :--- | :---: | :---: | :--- |
| `DATN_DEV01_R3_S1_INDEPENDENT_EDGE_GATES.py` | Kiểm toán biên F5 & F6 độc lập | 5 / 5 | **100% PASS** | Cả 3 lỗi ban đầu đều đã được khắc phục hoàn toàn |
| `tests/unit/test_r3_proof_gate_regression.py` | Kiểm thử hồi quy cổng chứng minh R3-S2 | 16 / 16 | **100% PASS** | Bổ sung 6 ca kiểm thử chuyên sâu cho F5 & F6 |
| Toàn bộ kiểm thử nội bộ (`pytest -v`) | Kiểm thử đơn vị, tích hợp, bảo mật, smoke | 135 / 135 | **100% PASS** | Bảo toàn toàn diện, không phát sinh hồi quy |
| `DATN_DEV01_R2_INDEPENDENT_GATE_TESTS.py` | Cổng kiểm toán R2 độc lập | 7 / 7 | **100% PASS** | Triệt tiêu epsilon rò rỉ, bảo toàn miền nghiệm |
| `DATN_DEV01_R2_INDEPENDENT_RECHECK.py` | Tái kiểm tra toán học R2 độc lập | 6 / 6 | **100% PASS** | M4, miền rỗng, AST round-trip |
| `DATN_DEV01_R3_NEW_GATE_TESTS.py` | Cổng kiểm toán R3 độc lập | 7 / 7 | **100% PASS** | F1..F4 (chống tiêm mã, chống chứng chỉ giả) |

---

### 6. TUÂN THỦ RANH GIỚI VÀ PHẠM VI NGHIÊN CỨU

1. **Không mở rộng ngoài phạm vi DEV-01:**
   - Hoàn toàn không triển khai DEV-02 (không có vector database, embedding, ChromaDB, FAISS).
   - Hoàn toàn không kết nối LLM, prompt engineering hay API mô hình ngôn ngữ.
   - Không xây dựng giao diện người dùng (UI/Web/Desktop).
2. **Không thay đổi các kỳ vọng kiểm thử chuẩn (gold tests):**
   - Giữ nguyên toàn bộ các assert gốc của người điều phối kiểm toán.
   - Không áp dụng số liệu giả hay báo cáo sai lệch.
3. **An toàn bảo mật:**
   - Giữ vững nguyên tắc cấm hoàn toàn `eval`, `exec`, `sympify` trên chuỗi đầu vào chưa được xác thực.

---

### 7. KẾT LUẬN & BÀN GIAO

Bản vá DEV-01-R3-S2 đã giải quyết trọn vẹn và triệt để hai lỗ hổng ranh giới tin cậy F5 và F6 được phát hiện trong đợt kiểm toán độc lập ngày 25/09/2026.
Toàn bộ mã nguồn, tài liệu kiểm toán, bộ test hồi quy và tệp lưu trữ nén `math_knowledge_engine_dev01_r3_s2.zip` đã được đóng gói sẵn sàng cho đợt nghiệm thu cuối cùng của DEV-01.
