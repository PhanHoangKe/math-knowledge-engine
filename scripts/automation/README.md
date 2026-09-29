# MKE Autonomous Development Bridge Setup Guide

Tài liệu này hướng dẫn cách kích hoạt quy trình tự động hóa giữa **Antigravity (Implementer)**, **GitHub (Repository)** và **ChatGPT (Independent Auditor)** cho dự án `math-knowledge-engine`.

---

## 1. Cơ chế Hoạt động

1. **Giao việc:** Project Owner (hoặc ChatGPT) tạo một GitHub Issue hoặc gửi feedback qua Pull Request.
2. **Tiếp nhận & Thực thi:** Daemon `mke_bridge_daemon.py` tự động phát hiện task mới $\to$ kích hoạt Antigravity sinh mã nguồn $\to$ chạy toàn bộ 6 bộ kiểm thử $\to$ sinh raw logs và manifest.
3. **Phát hành Evidence:** Daemon tự động tạo 2 commit riêng biệt:
   - Commit 1: Source & Unit Tests (`feat(...)`)
   - Commit 2: Evidence Logs (`docs(evidence): ...`)
4. **Kiểm toán tự động:** Pull Request được gửi đến ChatGPT để đánh giá. Nếu có lỗi (`REMEDIATE`), daemon tự động lặp lại quy trình sửa mà không cần can thiệp thủ công.
5. **Duyệt cuối cùng:** Khi ChatGPT báo cáo `AUDIT PASSED`, Owner chỉ cần bấm Approve để Tag/Release.

---

## 2. Cài đặt & Cấu hình

### Bước 1: Tạo GitHub Personal Access Token (PAT)
1. Truy cập `GitHub Settings` $\to$ `Developer settings` $\to$ `Personal access tokens` $\to$ `Tokens (classic)`.
2. Tạo token mới với các quyền:
   - `repo` (toàn quyền truy cập repository, commit, pull request, comment).
   - `workflow` (tùy chọn nếu có trigger actions).
3. Lưu token lại (ví dụ: `ghp_xxxxxxxxxxxx`).

### Bước 2: Thiết lập biến môi trường
Trên terminal PowerShell:
```powershell
$env:GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"
$env:GITHUB_REPOSITORY = "PhanHoangKe/math-knowledge-engine"
$env:MKE_POLL_INTERVAL_SEC = "30"
```

### Bước 3: Khởi chạy Daemon
```powershell
python scripts/automation/mke_bridge_daemon.py
```

---

## 3. Các Rào chắn An toàn (Safety Invariants)

- **Quy tắc 2 Commit:** Mã nguồn và nhật ký kiểm thử luôn được tách biệt.
- **Khóa Baseline P1B:** Daemon sẽ lập tức dừng lại nếu có bất kỳ thay đổi nào tác động vào các tệp CAS đóng băng hoặc các release tags trước đó.
- **Giới hạn số vòng sửa:** Mặc định tối đa 5 vòng remediation để chống vòng lặp vô tận.
- **Bảo mật dữ liệu:** Mọi đường dẫn thư mục máy cục bộ và token nhạy cảm đều được tự động làm sạch (`[REDACTED_PATH]`).
