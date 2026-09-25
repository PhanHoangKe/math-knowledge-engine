# DATN — KIỂM TOÁN ĐỘC LẬP DEV-01-R3
Ngày: 24/09/2026 (giờ Việt Nam)
Đối tượng kiểm toán: ZIP do người dùng cung cấp math_knowledge_engine_dev01_r3.zip
SHA-256 tính lại: 86f63fb99934260f3d5ade6dbf0a7b3c483e376680bd61ecfa0f233b1f18e57f
Kích thước: 147.978 byte; 69 mục ZIP. ZIP không kèm .git, vì vậy Git HEAD a744c92 và trạng thái working tree sạch trong báo cáo của coding AI chưa được xác minh độc lập.

## I. Đối chiếu thực thi
Kiểm toán thực hiện trên Linux, Python 3.13.x (khác môi trường Windows/Python 3.10.11 do coding AI báo cáo), SymPy 1.14.0, pytest 9.0.2, Pydantic 2.13.4. Không thay đổi mã nguồn bên trong ZIP.
- Toàn bộ pytest trong ZIP: 124 PASS khi chạy độc lập.
- Bảy bài Gate R2 đi kèm ZIP: 7/7 PASS (không được coi là độc lập chỉ vì tên gọi).
- Sáu bài recheck R2 đi kèm ZIP: 6/6 PASS.
- Bộ tám bài phản biện R1 ở ngoài ZIP từ hồ sơ cũ: 8/8 PASS.
- Đối chiếu mở rộng mang tính thăm dò: 40 phương trình phân thức tạo từ 8 tử số và 5 mẫu số đã định trước, trong đó engine chứng nhận hoàn chỉnh 35 và trả một phần 5. Với 35 ca có tập nghiệm hữu hạn đối chiếu được, 0 sai khác tìm thấy sau khi sửa script đối chiếu để bảo toàn giả thiết x thực. Đây không phải chứng minh tính đúng tuyệt đối hoặc thí nghiệm H1.

Kết luận riêng về các mục tiêu R3: Các lỗi epsilon-pass và thiếu nghiệm đã từng phát hiện trong R2 không tái xuất hiện trong các bài kiểm thử được chạy. Bằng chứng hiện có ủng hộ việc phần lõi toán học đã cải thiện rõ rệt, nhưng không đủ cho nghiệm thu toàn bộ giao diện kiểm chứng khi còn các vấn đề ở phần II.

## II. Phát hiện mới bằng kiểm thử ngoài repository
Tệp DATN_DEV01_R3_NEW_GATE_TESTS.py nằm ngoài repository được bàn giao. Kết quả: 3 PASS, 4 FAIL, ghi nguyên gốc trong DATN_DEV01_R3_NEW_GATE_TESTS_OUTPUT.txt. Các chuỗi kiểm thử chỉ dùng phép cộng số nguyên vô hại, không gọi lệnh hệ thống hay ghi tệp.

### F1 — CRITICAL FOR FUTURE EXTERNAL INTEGRATION: check_root_satisfaction() đánh giá chuỗi không tin cậy
Tệp: src/mke/models/domain.py, hàm check_root_satisfaction, nhánh fallback trả về sympy.sympify(cert.residue) khi phần dư là chuỗi. Với expr=x, ứng viên "__import__('builtins').sum((7, 11))", verify_root_exact() đã từ chối ứng viên đúng cách (STRING_PARSE_FAILURE), nhưng hàm tương thích lại diễn giải chuỗi và trả (False, 18). Điều này vi phạm nguyên tắc không đưa chuỗi chưa kiểm soát vào sympify.
Giới hạn bằng chứng: Chưa chứng minh chuỗi này có đường đi từ CLI hiện tại đến hàm trên. Đây là bề mặt API cấp thấp phải làm sạch trước khi H1 nhận dữ liệu ngoài.

### F2 — CRITICAL FOR PROOF BOUNDARY: completeness auditor diễn giải chuỗi không tin cậy và cấp PASS khi chưa qua exact gate
Tệp: src/mke/verification/completeness.py, dòng chuyển các phần tử verified_roots: List[str] qua sympy.sympify(vr_str) và bỏ qua ngoại lệ. Truyền trực tiếp phương trình x-18=0 kèm chuỗi "__import__('builtins').sum((7, 11))" làm hàm cấp COMPLETENESS=PASS, mặc dù đầu vào không phải bản ghi nghiệm đã được cổng xác minh chính xác chứng nhận. Đây vừa là rủi ro kiểm soát chuỗi đầu vào, vừa là API cho phép gọi completeness mà không cần chứng cứ soundness.
Giới hạn bằng chứng: Luồng VerificationEngine.verify() thông thường tạo verified_roots sau cổng xác minh chính xác. Kiểm thử chưa chứng minh engine/CLI có đường đi trực tiếp từ chuỗi đề bài đến hiện tượng F2. Tuy nhiên, để tích hợp truy xuất từ nguồn ngoài, API kiểm toán phải là fail-closed ngay tại ranh giới tiếp nhận dữ liệu.

### F3 — MAJOR CONTRACT INCONSISTENCY: Miền rỗng nhưng danh sách nghiệm được chứng nhận không rỗng
Tệp: src/mke/verification/completeness.py, nhánh domain.is_empty_domain trả PASS không kiểm tra verified_roots. Với phương trình x/0=0 và danh sách ["1"], API vẫn cấp COMPLETENESS=PASS. Luồng engine hiện đi nhánh miền rỗng trước, do đó đây là lỗ hổng tính nhất quán của API kiểm toán độc lập, chưa phải lỗi đầu ra engine thông thường.

### F4 — SCIENTIFIC CERTIFICATE SEMANTICS: NUMERICAL_REFUTATION không phải chứng chỉ chính xác
Tệp: src/mke/models/domain.py, verify_root_exact() gắn nhãn EXACT_FAIL khi abs(raw_sub.evalf(50)) > 1e-6 và chú thích Provably non-zero, không cung cấp chặn sai số số học hoặc chứng chỉ đại số. Kiểm thử cụ thể với expr=x-1 và ứng viên số đại số thực CRootOf(z**3-z-1, 0) vào nhánh NUMERICAL_REFUTATION. Ứng viên đó thực sự không phải nghiệm; phát hiện ở đây không khẳng định kết quả số đang sai, mà khẳng định bằng chứng dạng xấp xỉ không đủ để gắn nhãn 'EXACT'. Các nguồn nghiệm bên ngoài trong H1 làm vấn đề nhãn quan trọng hơn.
Nếu không cung cấp chứng minh đại số hoặc khoảng bao với sai số được chứng nhận, cần dùng trạng thái UNRESOLVED hoặc một nhãn quan sát số riêng, không đồng nhất với EXACT_FAIL.

## III. Quyết định nghiệm thu
- Về phạm vi toán học thử nghiệm R3: công nhận kết quả vượt các bộ kiểm thử cố định và 40 ca phân thức thăm dò, không phát hiện sai nghiệm trên tập được đối chiếu.
- Về toàn bộ DEV-01 để tích hợp dữ liệu truy xuất H1: CHƯA NGHIỆM THU vì F1–F3 có kiểm thử tái hiện thất bại; F4 cần sửa ngữ nghĩa chứng nhận trước khi dùng gate cho nguồn ngoài.
- Không chuyển DEV-02, không dùng phiên bản này để tự tạo nhãn chuẩn nghiên cứu hoặc tiếp nhận dữ liệu từ bên thứ ba.
- Không tiếp tục thêm chức năng. Thực hiện một bản vá nhỏ R3-S1, sau đó chạy lại bộ kiểm thử cố định và kết thúc vòng DEV-01 nếu đạt. Không đặt mục tiêu bất khả thi là chứng minh không còn mọi lỗi phần mềm.

## IV. Điều kiện nghiệm thu R3-S1
1. Không còn sympify(str) hoặc Python evaluation trên chuỗi không tin cậy trong src/ tại mọi đường đi liên quan tới kiểm chứng nghiệm.
2. Completeness auditor chỉ nhận tập nghiệm đã qua chính cổng exact verification trên cùng normalized equation, hoặc tự tái kiểm tra độc lập các đối tượng typed trước khi xét đầy đủ. Mọi chuỗi không đúng schema phải từ chối an toàn.
3. API miền rỗng với danh sách nghiệm không rỗng không được cấp COMPLETENESS=PASS.
4. Không phát hành EXACT_FAIL chỉ dựa vào ngưỡng evalf chưa có chứng chỉ. Được phép UNRESOLVED.
5. Giữ nguyên kết quả 124 test trong ZIP và 8 + 7 + 6 test kiểm toán trước đó, và làm cho cả 7 test trong bộ mới đạt không sửa oracle/đáp án. Nếu phải thay đổi interface cũ, duy trì adapter an toàn và ghi rõ thay đổi.
6. Mã nguồn sửa đổi cần ZIP sạch, SHA-256, log kiểm thử thật, báo cáo và giới hạn còn tồn tại. Không tự tuyên bố "100% bảo mật/chính xác".

## V. Lệnh tái lập (trong thư mục ZIP đã giải nén)
PYTHONPATH=src python -m pytest -ra
PYTHONPATH=src python DATN_DEV01_R2_INDEPENDENT_GATE_TESTS.py
PYTHONPATH=src python DATN_DEV01_R2_INDEPENDENT_RECHECK.py
PYTHONPATH=src python -m pytest -q DATN_DEV01_R3_NEW_GATE_TESTS.py
