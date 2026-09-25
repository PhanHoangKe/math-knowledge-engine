# Pull Request: [DEV-02A] Method Knowledge Base & Handcrafted DEV_PILOT Dataset

## 1. Metadata
- **Base branch**: `dev01-accepted` (`c9199abf3148b4983d3f29cd214e164cef0aad9e`)
- **Compare branch**: `dev02a-method-knowledge-base` (`a9259306b9d8500981d6fcef21068d8f2792ced3`)
- **Mục tiêu**: Xây dựng hạ tầng biểu diễn tri thức phương pháp giải đại số và bộ dữ liệu thử nghiệm pilot chuẩn bị cho việc nghiên cứu giả thuyết H1.

---

## 2. Git Diff Summary
- **Số tệp thay đổi**: 33 files (+3591 lines, -5 lines)
- **Các thành phần chính**:
  - `src/mke/knowledge/schemas.py`: Pydantic models (MethodTemplate, MethodInstance, FamilyRecord, ProblemRecord, MethodAnnotation, TransferPairRecord, DatasetManifest).
  - `src/mke/knowledge/provenance.py`: Serialization chuẩn tắc, SHA-256 hash độc lập với thời gian/OS.
  - `src/mke/knowledge/indexer.py`: SQLite indexer xác định với 5 bảng quan hệ và chỉ mục.
  - `src/mke/knowledge/repository.py`: Facade truy vấn dữ liệu từ JSONL và SQLite.
  - `src/mke/knowledge/validator.py`: Trình kiểm định toàn vẹn schema, khóa ngoại, không trùng lặp ID/biểu thức, ràng buộc split group.
  - `src/mke/knowledge/dev01_adapter.py`: Adapter kết nối bộ dữ liệu với bộ máy kiểm chứng DEV-01, phát hiện và lưu vết bất đồng.
  - `src/mke/cli/main.py`: Mở rộng nhóm lệnh `mke kb` (`validate`, `list-methods`, `show-method`, `list-families`, `inspect-problem`, `run-dev-validation`, `export-report`).
  - `data/knowledge/`: 5 phương pháp M1–M5 (`methods.jsonl`, `manifest.json`).
  - `data/dev_pilot/`: 15 họ, 41 bài toán, 43 chú giải, 4 cặp chuyển giao (`families.jsonl`, `problems.jsonl`, `annotations.jsonl`, `transfer_pairs.jsonl`, `manifest.json`).
  - `docs/`: 4 tài liệu đặc tả kiến trúc, giao thức dataset, hướng dẫn gán nhãn, chính sách chống rò rỉ dữ liệu.
  - `tests/knowledge/`: 6 tệp test với 31 bài kiểm thử mới.

---

## 3. Số Liệu Bộ Dữ Liệu DEV_PILOT
- **Họ bài toán (Families)**: 15 seed families, bao phủ 5 lớp phương trình (Linear, Quadratic, Factorable, Rational, Biquadratic).
- **Bài toán biến thể (Problems)**: 41 bài toán, **100% thuộc phân vùng `Split.DEV`** (zero rò rỉ sang validation/test).
- **Chú giải phương pháp (Annotations)**: 43 bản ghi, mỗi bản ghi gắn chặt với `problem_id`, `method_id`, `method_version`, `method_instance_id`.
- **Cặp chuyển giao (Transfer Pairs)**: 4 cặp chuyển giao đánh giá tính an toàn khi tái sử dụng nghiệm, trong đó `FAM_04` $\rightarrow$ `FAM_11` là chuyển giao không an toàn (`UNSAFE_COPY`).
- **Nhóm phân vùng chống rò rỉ (`split_group_id`)**: `FAM_04_QUAD_TWO_ROOTS` và `FAM_11_RAT_EXTRANEOUS_TRANSFER` bắt buộc chung nhóm `SG_QUAD_RAT_TRANSFER`.

---

## 4. Kết Quả Kiểm Thử Thực Tế
- **Toàn bộ Test Suite Repository (`pytest -v`)**: **166 / 166 PASSED** (4.65s)
  - 135 tests nền tảng DEV-01 (regression R1, R2, R3, R3-S1, R3-S2): **135/135 PASSED**.
  - 31 tests tri thức & dữ liệu mới (`tests/knowledge/`): **31/31 PASSED**.
- **Các Cổng Thử Độc Lập Bên Ngoài**:
  - `DATN_DEV01_R2_INDEPENDENT_GATE_TESTS.py`: 7/7 PASSED.
  - `DATN_DEV01_R2_INDEPENDENT_RECHECK.py`: 6/6 PASSED.
  - `DATN_DEV01_R3_NEW_GATE_TESTS.py`: 7/7 PASSED.
  - `DATN_DEV01_R3_S1_INDEPENDENT_EDGE_GATES.py`: 5/5 PASSED.
- **Kiểm định dữ liệu (`mke kb validate`)**:
  - `is_valid: True`, `total_errors: 0`, `total_warnings: 0`.

---

## 5. Báo Cáo 7 Bất Đồng Toán Học (Preserved Discrepancies)
Được lưu trữ chi tiết tại: `reports/DEV02A_DISCREPANCIES.json`
Toàn bộ bất đồng được bảo tồn nguyên vẹn để phục vụ nghiên cứu phản biện, không bị can thiệp ép sửa nhãn:
1. `PROB_FAM02_V01` ($0x = 0$): Phương trình đồng nhất thức trên $\mathbb{R}$. Engine DEV-01 chứng nhận vô số nghiệm trên miền xác định (`is_identity_on_domain=True`), khác với kỳ vọng tập nghiệm cụ thể trong nhãn sơ bộ.
2. `PROB_FAM02_V02` ($0x = 5$): Phương trình vô nghiệm mâu thuẫn ($0 = 5$).
3. `PROB_FAM12_V01` ($\frac{x-2}{x-2} = 1$): Đồng nhất thức trên miền xác định có lỗ thủng $\mathbb{R} \setminus \{2\}$.
4. `PROB_FAM12_V02` ($\frac{x}{x-x} = 0$): Miền xác định rỗng từ đầu ($\emptyset$), phương pháp bị bác bỏ, nghiệm rỗng được chứng minh thuần túy bởi chứng chỉ miền xác định.
5. `PROB_FAM12_V03` ($\frac{1}{x-2} = 0$): Không có nghiệm thỏa mãn trên miền xác định.
6. `PAIR_FAM04_V01_TO_FAM11_V01`: Chuyển giao nghiệm $x \in \{2, 3\}$ từ $x^2 - 5x + 6 = 0$ sang $\frac{x^2 - 5x + 6}{x - 2} = 0$ bị phát hiện là `UNSAFE_COPY` do nghiệm $x = 2$ triệt tiêu mẫu số.
7. `PAIR_FAM04_V02_TO_FAM11_V02`: Tương tự cho biến thể thứ hai của cặp chuyển giao nghiệm ngoại lai.

---

## 6. Trạng Thái Nhãn Gán & Giới Hạn Nghiên Cứu
- **Trạng thái nhãn gán**: 100% (43/43) các bản ghi gán nhãn phương pháp đều mang trạng thái `review_status = ReviewStatus.PROVISIONAL`. Hệ thống không tuyên bố đây là bộ nhãn vàng tuyệt đối.
- **Giới hạn chưa giải quyết**:
  - DEV-02A chỉ mới là bộ dữ liệu phát triển thử nghiệm (`DEV_PILOT`), chưa thể hiện tính khái quát hóa cho các phân vùng `VALIDATION` hoặc `TEST` trong tương lai.
  - Phân hệ này chưa tích hợp vector database, BM25, dense embeddings hay LLM (chờ phân hệ DEV-02B theo lộ trình nghiên cứu).
  - Không merge Pull Request này trước khi Người điều phối nghiên cứu hoàn tất kiểm toán độc lập.
