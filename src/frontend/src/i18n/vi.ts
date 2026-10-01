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
  
  panel_skeleton_input_analysis: 'Phân tích Biểu thức Đầu vào (Chờ truy vấn)',
  panel_skeleton_canonical_form: 'Dạng Chuẩn tắc & Hệ số (Chờ truy vấn)',
  panel_skeleton_methods: 'Phương pháp Khả dụng (Chờ truy vấn)',
  panel_skeleton_solution_trace: 'Lời giải Từng bước & Minh chứng (Chờ truy vấn)',
  
  shell_status_idle: 'Trạng thái: Sẵn sàng (Frontend Shell v1.0.0)',
  shell_status_note: 'Động cơ giải trực tiếp sẽ được kích hoạt tại Giai đoạn S2-04.',

  flow_tagline: 'Kiến trúc Toán học Tất định MKE:',
  flow_ast: 'Cú pháp AST Tường minh',
  flow_rational: 'Số học Hữu tỉ \\(\\mathbb{Q}\\)',
  flow_symbolic: 'Suy luận Ký hiệu \\(\\mathbb{R}\\)',
  flow_cert: 'Nghiệm & Minh chứng Tất định',

  footer_copyright: '© 2026 Math Knowledge Engine Project. Bản quyền thuộc về Kế Phan Hoàng.',
} as const;

export type TranslationKey = keyof typeof vi;
export type Translations = Record<TranslationKey, string>;
