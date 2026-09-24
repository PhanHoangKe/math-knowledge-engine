# Math Knowledge Engine (DEV-01)
## Mathematical Verification Foundation for Algebraic Equations

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/DEV--01-PASSED-brightgreen.svg)]()

Hệ thống **Math Knowledge Engine** (MKE) là nền tảng giải và xác minh toán học đại số phục vụ đề tài nghiên cứu tốt nghiệp CNTT:
> *"Nghiên cứu và thực nghiệm truy xuất, tái sử dụng phương pháp giải phương trình đại số có kiểm tra điều kiện áp dụng và nghĩa vụ chứng minh."*

Nhiệm vụ **DEV-01** hoàn thành nền tảng xác minh toán học cốt lõi (*Mathematical Verification Foundation*), đảm bảo tính toán an toàn, bảo toàn miền xác định toán học ban đầu và xây dựng danh mục 5 phương pháp giải với nghĩa vụ chứng minh hình thức.

---

## 1. Kiến Trúc Hệ Thống

```text
Math Knowledge Engine/
├── pyproject.toml              # Cấu hình dự án và packaging
├── requirements.txt            # Danh sách dependencies ghim phiên bản
├── README.md                   # Hướng dẫn sử dụng và tái lập
├── docs/                       # Tài liệu nghiên cứu chi tiết
│   ├── mathematical_scope.md   # Phạm vi toán học và giới hạn
│   ├── security_limitations.md # Cơ chế an toàn và phòng chống tấn công
│   └── data_leakage_prevention.md # Quy trình quản lý dữ liệu nghiên cứu
├── src/mke/                    # Mã nguồn cốt lõi
│   ├── models/                 # Schemas, Enums, AST Nodes, Evidence models
│   ├── parsing/                # Safe Lexer, Parser, SymPy Converter, Normalizer
│   ├── domain/                 # Domain extractor từ unreduced AST
│   ├── methods/                # Catalogue 5 phương pháp (M1 - M5)
│   ├── verification/           # Verification Engine & Solution Transfer Auditor
│   ├── audit/                  # Smoke runner & JSON audit report generator
│   └── cli/                    # Giao diện dòng lệnh Typer/Rich
├── tests/                      # Bộ kiểm thử toàn diện (75 tests)
│   ├── unit/                   # Kiểm thử đơn vị cho lexer, parser, domain, methods
│   ├── integration/            # Kiểm thử tích hợp pipeline
│   ├── property/               # Kiểm thử bất biến với independent oracle
│   ├── security/               # Kiểm thử chống injection và DoS limits
│   └── smoke/                  # Bộ smoke test bắt buộc T1 - T8
├── data/                       # Dữ liệu phục vụ kiểm thử
│   ├── smoke/                  # Fixture kiểm toán độc lập T1 - T8
│   └── dev/                    # Mẫu bài toán khảo sát phát triển
└── reports/                    # Báo cáo nghiệm thu và kiểm toán
    ├── DEV01_IMPLEMENTATION_REPORT.md
    └── DEV01_AUDIT.json
```

---

## 2. Yêu Cầu Môi Trường & Cài Đặt

### Yêu Cầu
- Hệ điều hành: Windows, Linux hoặc macOS (CPU-first, không yêu cầu GPU).
- Python: 3.10+ (Đã thẩm định trên Python 3.10.11 và tương thích Python 3.12).
- Không yêu cầu API trả phí, không kết nối Internet sau khi cài đặt.

### Cài Đặt
```powershell
# Di chuyển vào thư mục dự án
cd "d:\Math Knowledge Engine"

# Cài đặt gói ở chế độ editable với dependencies ghim phiên bản
python -m pip install -e .
```

---

## 3. Hướng Dẫn Sử Dụng CLI

Công cụ dòng lệnh `mke` cung cấp các tính năng khảo sát toán học:

### 3.1. Phân Tích Cú Pháp An Toàn (`parse`)
Kiểm tra biểu thức theo grammar hữu hạn, từ chối an toàn mọi toán tử/hàm ngoài phạm vi.
```powershell
mke parse "x^2 - 5*x + 6 = 0"
```

### 3.2. Kiểm Tra Bảo Toàn Miền Xác Định (`domain`)
Trích xuất miền xác định $\mathbb{R} \setminus S$ từ AST chưa rút gọn trước mọi thao tác đại số:
```powershell
mke domain "(x - 2) / (x - 2) = 1"
```
*Kết quả:* Bảo toàn điều kiện $x \neq 2$, miền xác định là $\mathbb{R} \setminus \{2\}$ ngay cả khi phương trình rút gọn thành $1 = 1$.

### 3.3. Đánh Giá Danh Mục Phương Pháp (`methods`)
Đánh giá điều kiện áp dụng (guards) của 5 phương pháp đối với phương trình:
```powershell
mke methods "x^2 + 1 = 0"
```

### 3.4. Xác Minh Toàn Diện (`verify`)
Thực thi kiểm tra điều kiện, giải nghiệm và thẩm định nghĩa vụ chứng minh:
```powershell
mke verify "x^2 - 5*x + 6 = 0"
mke verify "(x^2 - 5*x + 6) / (x - 2) = 0"
mke verify "sqrt(x + 2) = x"
```

### 3.5. Chạy Bộ Smoke Test T1 - T8 (`smoke`)
Chạy bộ kiểm thử độc lập đối với 8 trường hợp nghiên cứu bắt buộc:
```powershell
mke smoke
```

### 3.6. Xuất Báo Cáo Kiểm Toán JSON (`report`)
Tạo báo cáo kiểm toán có cấu trúc `DEV01_AUDIT.json`:
```powershell
mke report --output reports/DEV01_AUDIT.json
```

---

## 4. Chạy Toàn Bộ Kiểm Thử (Testing)

```powershell
# Chạy toàn bộ 75 tests
python -m pytest -v

# Chạy riêng bộ smoke test
python -m pytest tests/smoke/test_smoke_cases.py -v

# Chạy kiểm thử bảo mật
python -m pytest tests/security/test_security.py -v

# Chạy kiểm thử bất biến (Property-based tests)
python -m pytest tests/property/test_properties.py -v
```

---

## 5. Kết Quả Nghiệm Thu DEV-01

- **Tổng số tests**: 75/75 PASS (100%).
- **Bộ smoke bắt buộc T1 - T8**: 8/8 PASS.
- **Thời gian chạy toàn bộ test**: ~0.42 giây trên CPU máy tính thông thường.
- **Bảo mật**: Tuyệt đối không sử dụng `eval()`, `exec()`, `sympify()` trên chuỗi tự do.
- **Tài liệu kiểm toán**: Xem chi tiết tại [DEV01_IMPLEMENTATION_REPORT.md](reports/DEV01_IMPLEMENTATION_REPORT.md) và [DEV01_AUDIT.json](reports/DEV01_AUDIT.json).
