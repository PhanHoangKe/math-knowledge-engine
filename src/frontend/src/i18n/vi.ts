/**
 * MKE MVP V1 — Vietnamese Localization Resource (Default).
 */
export const vi = {
  app_title: 'Math Knowledge Engine',
  app_subtitle: 'Math Knowledge Engine',
  brand_alpha: 'Alpha',
  product_badge: 'MVP V1',
  product_badge_title: 'MKE MVP V1 — Không gian làm việc Đại số Tất định',
  
  nav_home: 'Trang chủ',
  nav_workspace: 'Đại số',
  nav_syntax: 'Cú pháp',
  nav_main_aria: 'Điều hướng chính',
  header_signin: 'Đăng nhập',

  settings_trigger_aria: 'Tùy chọn chủ đề & ngôn ngữ',
  settings_title: 'Cài đặt hệ thống',
  theme_title: 'Giao diện',
  theme_auto: 'Tự động',
  theme_light: 'Sáng',
  theme_dark: 'Tối',
  lang_title: 'Ngôn ngữ',
  lang_vi: 'Tiếng Việt',
  lang_en: 'English',

  hero_super: 'HỆ THỐNG SUY LUẬN KÝ HIỆU HÌNH THỨC & TOÁN HỌC CHUẨN XÁC',
  hero_title: 'Math Knowledge Engine',
  hero_tagline: '"Suy luận ký hiệu tất định trên miền số thực \\(\\mathbb{R}\\) với số học hữu tỉ chuẩn xác trên \\(\\mathbb{Q}\\)"',

  input_placeholder: 'Nhập phương trình đại số (ví dụ: x^2 - 5*x + 6 = 0)...',
  input_aria: 'Nhập phương trình đại số',
  input_label: 'Phương trình đại số:',
  clear_btn_aria: 'Xóa nội dung nhập',
  compute_btn_aria: 'Phân tích và giải phương trình',
  compute_btn_text: '=',
  quick_keys_label: 'Phím nhanh:',

  empty_workspace_title: 'Không gian Làm việc Đại số',
  empty_workspace_msg: 'Nhập phương trình để bắt đầu phân tích.',
  empty_workspace_sub: 'Hệ thống sẽ thực hiện phân tích cú pháp AST, phân loại bậc phương trình, kiểm tra khả năng áp dụng phương pháp và chứng minh nghiệm qua chứng chỉ xác thực tất định.',
  shell_status_note: 'Hệ thống sẵn sàng tiếp nhận và giải phương trình đại số.',
  panel_skeleton_input_analysis: 'Phân tích Biểu thức Đầu vào (Chờ truy vấn)',
  panel_skeleton_canonical_form: 'Dạng Chuẩn tắc & Hệ số (Chờ truy vấn)',
  panel_skeleton_methods: 'Phương pháp Khả dụng (Chờ truy vấn)',
  panel_skeleton_solution_trace: 'Minh chứng Lời giải Từng bước (Chờ truy vấn)',
  
  shell_status_idle: 'Trạng thái: Sẵn sàng (Động cơ Toán học Tất định)',
  shell_status_loading: 'Đang gửi truy vấn và phân tích trên máy chủ toán học...',
  shell_status_solved: 'Trạng thái: Đã giải và xác thực toàn diện',
  shell_status_analyzed: 'Trạng thái: Đã phân tích (Không thực thi lời giải)',
  shell_status_error: 'Trạng thái: Lỗi phân tích cú pháp / tham số',

  flow_tagline: 'Kiến trúc Toán học Tất định MKE:',
  flow_ast: 'Cú pháp AST Tường minh',
  flow_rational: 'Số học Hữu tỉ \\(\\mathbb{Q}\\)',
  flow_symbolic: 'Suy luận Ký hiệu \\(\\mathbb{R}\\)',
  flow_cert: 'Nghiệm & Minh chứng Tất định',

  footer_copyright: '© 2026 Math Knowledge Engine Project. Bản quyền thuộc về Kế Phan Hoàng.',

  // --- S2-04 Live Workspace Localization ---
  state_loading: 'Đang xử lý phân tích toán học trên máy chủ...',
  btn_retry: 'Thử lại',
  btn_clear: 'Xóa',
  btn_switch_method: 'Giải phương pháp này',
  btn_selected_method: 'Đang chọn',

  panel_canonical_problem: 'Biểu thức Chuẩn tắc & Hệ số',
  panel_method_catalog: 'Danh mục Phương pháp Giải',
  panel_solution_summary: 'Kết luận & Nghiệm Thực',
  panel_solution_trace: 'Minh chứng Lời giải Từng bước',
  panel_verification: 'Chứng chỉ Xác thực Độc lập',
  panel_degenerate_solution: 'Lời giải Phương trình Suy biến',

  lbl_problem_id: 'Mã bài toán (Problem ID)',
  lbl_semantic_hash: 'Mã băm ngữ nghĩa (Semantic Revision Hash)',
  lbl_classification: 'Phân loại',
  lbl_coefficients: 'Hệ số chuẩn tắc',
  lbl_discriminant: 'Biệt thức \\(\\Delta\\)',
  lbl_discriminant_perfect_square: 'Chính phương trong \\(\\mathbb{Q}\\)',
  lbl_discriminant_positive: 'Dương (\\(\\Delta > 0\\))',
  lbl_discriminant_zero: 'Bằng 0 (\\(\\Delta = 0\\))',
  lbl_discriminant_negative: 'Âm (\\(\\Delta < 0\\))',

  lbl_method_applicability: 'Khả dụng toán học',
  lbl_method_recommendation: 'Khuyến nghị sư phạm',
  lbl_method_verification: 'Khả năng xác thực',
  lbl_method_reasons: 'Lý do áp dụng',
  lbl_method_prerequisites: 'Điều kiện tiên quyết',
  lbl_method_trace_available: 'Có lời giải chi tiết',

  enum_app_APPLICABLE: 'Khả dụng',
  enum_app_NOT_APPLICABLE: 'Không khả dụng',
  enum_app_UNKNOWN: 'Chưa xác định',

  enum_rec_RECOMMENDED: 'Khuyến nghị',
  enum_rec_NEUTRAL: 'Trung tính',
  enum_rec_DISCOURAGED: 'Không khuyến khích',

  enum_ver_HOST_VERIFIABLE: 'Xác thực Độc lập',
  enum_ver_UNVERIFIED: 'Chưa xác thực',
  enum_ver_NOT_APPLICABLE: 'Không áp dụng',

  enum_sup_SUPPORTED: 'Đã hỗ trợ',
  enum_sup_UNSUPPORTED: 'Chưa hỗ trợ',

  enum_exec_AVAILABLE: 'Sẵn sàng giải',
  enum_exec_UNAVAILABLE: 'Chưa khả dụng',

  lbl_solution_outcome: 'Kết luận nghiệm',
  lbl_final_answer: 'Tập nghiệm \\(S\\)',
  lbl_roots_list: 'Danh sách nghiệm thực',
  lbl_root_approx: 'Xấp xỉ thập phân',
  lbl_no_roots: 'Phương trình vô nghiệm trên miền số thực \\(\\mathbb{R}\\)',

  enum_out_TWO_DISTINCT_REAL_ROOTS: '2 nghiệm thực phân biệt',
  enum_out_ONE_REPEATED_REAL_ROOT: '1 nghiệm thực kép',
  enum_out_NO_REAL_ROOTS: 'Vô nghiệm trên \\(\\mathbb{R}\\)',
  enum_out_ONE_REAL_LINEAR_ROOT: '1 nghiệm bậc nhất duy nhất',
  enum_out_INFINITE_REAL_SOLUTIONS: 'Vô số nghiệm (Đồng nhất thức)',
  enum_out_NO_REAL_SOLUTIONS_CONTRADICTION: 'Vô nghiệm (Mâu thuẫn)',

  lbl_trace_disclaimer: 'Lời giải từng bước mang tính diễn giải sư phạm tất định. Phạm vi xác thực toán học độc lập là kết quả nghiệm cuối cùng.',
  lbl_trace_step: 'Bước',
  lbl_trace_rule: 'Quy tắc / Định lý',
  lbl_trace_why: 'Mục đích bước này',

  lbl_cert_id: 'Mã chứng chỉ (Certificate ID)',
  lbl_cert_outcome: 'Kết quả xác thực',
  lbl_cert_scope: 'Phạm vi xác thực',
  lbl_cert_verifier: 'Động cơ xác thực',
  lbl_cert_timestamp: 'Thời gian xác thực (UTC)',
  lbl_cert_fingerprint: 'Dấu vân tay tính toàn vẹn (SHA-256)',
  lbl_cert_disclaimer: 'Dấu vân tay tính toàn vẹn là mã băm SHA-256 không khóa đại diện cho nội dung chứng chỉ được xác thực, không phải là chữ ký số mật mã học.',
  lbl_cert_multiplicity: 'Xác thực số bội nghiệm',
  lbl_cert_vieta: 'Kiểm tra hệ thức Viète',
  lbl_cert_identities: 'Đồng nhất thức đại số đã qua',
  lbl_cert_residuals: 'Kiểm tra độ lệch dư',

  enum_ver_out_VERIFIED_COMPLETE: 'Xác thực Toàn diện Thành công',
  enum_ver_out_VERIFICATION_FAILED: 'Xác thực Thất bại',
  enum_ver_out_NOT_APPLICABLE: 'Không áp dụng xác thực',

  lbl_reason_code: 'Lý do phân tích',
  lbl_reason_METHOD_NOT_EXECUTABLE: 'Phương pháp chưa hỗ trợ thuật toán thực thi chi tiết.',
  lbl_reason_METHOD_NOT_APPLICABLE: 'Phương pháp không áp dụng được về mặt toán học cho phương trình này.',
  lbl_reason_DEGENERATE_EXACT_SOLUTION: 'Phương trình suy biến (bậc nhất / đồng nhất / vô nghiệm).',
  lbl_analysis_msg: 'Thông điệp phân tích từ máy chủ',

  err_app_title: 'Lỗi Phân tích Đại số',
  err_transport_title: 'Lỗi Truyền tải Giao thức (HTTP)',
  err_network_title: 'Không thể kết nối máy chủ',
  err_network_msg: 'Không thể kết nối đến máy chủ toán học MKE. Vui lòng kiểm tra kết nối mạng và thử lại.',
  err_protocol_title: 'Phản hồi không hợp lệ',
  err_protocol_msg: 'Máy chủ trả về phản hồi không đúng giao thức quy định.',
  err_code_lbl: 'Mã lỗi',
  err_span_lbl: 'Vị trí lỗi trên chuỗi nhập',
  err_details_lbl: 'Chi tiết kỹ thuật',
} as const;

export type TranslationKey = keyof typeof vi;
export type Translations = Record<TranslationKey, string>;
