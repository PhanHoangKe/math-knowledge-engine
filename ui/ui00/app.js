/**
 * MKE PRODUCT-UI-00 — Bilingual Client-Side Prototype Logic
 * Strictly self-contained: Zero external network requests, zero CDNs, local storage persistence.
 * English identifiers in source code; user-facing content sourced exclusively from I18N resources.
 */

(function () {
  'use strict';

  // ==========================================================================
  // Localization Dictionary (Structured I18N)
  // ==========================================================================
  const I18N = {
    vi: {
      // Header & Navigation
      brand_subtitle: 'Hệ thống Tri thức Toán học',
      brand_home_aria: 'Trang chủ MKE',
      prototype_badge: 'UI-00 BẢN MẪU',
      prototype_badge_title: 'Bản mẫu trực quan (Chưa kết nối backend)',
      nav_main_aria: 'Điều hướng chính',
      nav_home: 'Trang chủ',
      nav_sample: 'Kết quả mẫu',
      nav_syntax: 'Cú pháp',
      lang_label: 'Ngôn ngữ:',
      lang_select_aria: 'Chọn ngôn ngữ giao diện',
      theme_label: 'Giao diện:',
      theme_select_aria: 'Chọn chủ đề màu',
      theme_auto: 'Tự động (Hệ thống)',
      theme_light: 'Sáng',
      theme_dark: 'Tối',

      // Advisory Banner
      banner_tag: 'BẢN MẪU / DỮ LIỆU DEMO',
      banner_msg: 'Đây là bản mẫu giao diện trực quan độc lập. Mọi kết quả toán học hiển thị chỉ mang tính chất minh họa giả lập; chưa kết nối với bộ giải hay backend chính thức.',

      // Home Screen — Hero & Search
      hero_title: 'Tri thức Toán học Chuẩn xác & Tính toán Kiểm chứng được',
      hero_subtitle: 'Suy luận ký hiệu tất định trên miền số thực \\(\\mathbb{R}\\) với số học hữu tỉ chuẩn xác trên \\(\\mathbb{Q}\\).',
      input_placeholder: 'Nhập phương trình (ví dụ: 2*x + 3 = 7, -x^2 = 1, x^0 = 1)...',
      input_aria: 'Nhập biểu thức toán học',
      clear_title: 'Xóa nội dung nhập',
      clear_aria: 'Xóa nội dung nhập',
      compute_btn: 'Tính toán',
      compute_aria: 'Tính toán biểu thức',
      keyboard_aria: 'Phím chèn ký hiệu toán học',
      kb_hint: 'Chèn nhanh:',
      sym_mult: '* (nhân tường minh)',
      chips_aria: 'Các ví dụ tiêu biểu',
      chips_label: 'Ví dụ:',
      chip_syntax_demo: '1/2x = 1 (Lỗi Cú pháp Demo)',
      chip_syntax_title: 'Minh họa bắt lỗi nhân ngầm mơ hồ',

      // Home Screen — 4 Topic Cards
      topics_section_aria: 'Chuyên đề toán học',
      topics_title: 'Chuyên đề Toán học & Năng lực Xử lý',
      badge_p02a_active: 'GIAI ĐOẠN P02A HOẠT ĐỘNG',
      card_algebra_title: 'Đại số & Phương trình Tuyến tính',
      card_algebra_desc: 'Phương trình tuyến tính affine chuẩn xác ax + b = 0 trên miền thực \\(\\mathbb{R}\\) với hệ số hữu tỉ \\(\\mathbb{Q}\\). Xử lý chính xác đồng nhất thức và mâu thuẫn.',
      prompt_algebra_identity: '0*x = 0 (Đồng nhất thức trên \\(\\mathbb{R}\\))',

      badge_core_active: 'CỐT LÕI HOẠT ĐỘNG',
      card_rational_title: 'Số học Trường Số Hữu tỉ',
      card_rational_desc: 'Số học chính xác độ chính xác tùy ý trên \\(\\mathbb{Q}\\). Rút gọn GCD Euclid chuẩn tắc, triệt tiêu sai số trôi của số thực dấu phẩy động.',
      prompt_rational_domain: 'Điều kiện xác định: (x-1)/(x-1)',
      prompt_rational_bigint: 'Số nguyên lớn (10^100)',

      badge_planned_r1: 'DỰ KIẾN (R1)',
      card_quad_title: 'Phương trình Bậc hai & Phân tích Nhân tử',
      card_quad_desc: 'Phương trình phi tuyến ax^2 + bx + c = 0, tính biệt thức, khai triển bình phương và kiểm tra nghiệm ứng viên độc lập.',
      prompt_quad_candidate: 'x^2 - 4 = 0 (Kiểm tra nghiệm ứng viên)',
      prompt_quad_factoring: 'Phương pháp phân tích nhân tử (Dự kiến)',
      prompt_quad_radicals: 'Mở rộng trường căn thức (Dự kiến)',

      badge_planned_r2: 'DỰ KIẾN (R2)',
      card_classroom_title: 'Lớp học & Tiếp nhận Tài liệu',
      card_classroom_desc: 'Chẩn đoán sư phạm từng bước, phân loại lỗi học sinh và tiếp nhận tài liệu toán PDF/hình ảnh có kiểm soát riêng biệt.',
      prompt_class_tree: 'Cây hướng dẫn từng bước (Dự kiến)',
      prompt_class_pdf: 'Tiếp nhận tài liệu PDF thủ công (Dự kiến)',
      prompt_class_grade: 'Chấm điểm danh sách lớp (Dự kiến)',

      // Result Screen
      btn_back_home: '← Quay lại Trang chủ',
      active_query_label: 'Biểu thức đang chọn:',
      card_input_title: 'Phân tích Biểu thức Đầu vào',
      status_syntax_valid: 'CÚ PHÁP HỢP LỆ',
      status_syntax_invalid: 'CÚ PHÁP KHÔNG HỢP LỆ (TỪ CHỐI)',
      meta_grammar_label: 'Chuẩn ngữ pháp:',
      meta_mult_label: 'Phép nhân:',
      meta_mult_val: 'Tường minh (đã xác nhận *)',
      meta_mult_invalid_val: 'Phát hiện phép nhân ngầm mơ hồ',
      meta_ast_nodes_label: 'Nút AST:',
      meta_ast_nodes_val: '7 nút được bảo toàn',
      ast_summary: 'Xem Cấu trúc Cây Cú pháp (AST)',

      card_solution_title: 'Nghiệm Chuẩn xác',
      methods_aria: 'Phương pháp giải toán',
      tab_linear_algebra: 'Đại số Tuyến tính trên Trường',
      tab_factoring_planned: 'Phân tích Nhân tử (Dự kiến)',
      tab_graphic_planned: 'Dạng Đồ thị (Dự kiến)',
      tab_planned_r1_title: 'Dự kiến cho Bản phát hành 1',
      sol_domain_tag: 'Số hữu tỉ chính xác trong \\(\\mathbb{Q}\\)',
      trace_title: 'Các bước Biến đổi Tất định',

      card_domain_title: 'Miền Xác định & Minh chứng Kiểm định',
      badge_mock_specimen: 'BẢN MẪU MÔ PHỎNG (DEMO)',
      tile_eq_domain: 'Miền nghiệm phương trình',
      val_eq_domain: 'Số thực \\(\\mathbb{R}\\)',
      tile_domain_constraints: 'Ràng buộc miền ban đầu',
      tile_candidate_check: 'Kiểm tra nghiệm ứng viên',
      tag_specimen_notice: 'GHI CHÚ MINH HỌA GIAO DIỆN (DEMO)',
      msg_specimen_disclaimer: 'Khung hiển thị này chỉ minh họa cấu trúc biên nhận kiểm định trực quan. Bản mẫu hiện tại không sinh hoặc chứng nhận mã băm mật mã thực tế; cơ chế ký số chứng thực sẽ được tích hợp trong các mốc phát triển chính thức.',

      // Syntax Guide Screen
      syntax_guide_title: 'Quy chuẩn Cú pháp MKE Giai đoạn P02A',
      syntax_guide_lead: 'MKE áp dụng cú pháp toán học tường minh nghiêm ngặt nhằm loại trừ hoàn toàn các diễn giải mơ hồ hoặc ngầm định sai lệch.',
      syntax_accepted_title: '✓ Cú pháp Được Chấp nhận',
      syntax_acc_1: '(Phép nhân tường minh với ký tự *)',
      syntax_acc_2: '(Được phân tích thành -(x^2))',
      syntax_acc_3: '(Cơ số âm có dấu ngoặc nhóm)',
      syntax_acc_4: '(Bảo toàn nút lũy thừa; đánh giá trên miền ban đầu)',
      syntax_acc_5: '(Phương trình đồng nhất; miền nghiệm \\(\\mathbb{R}\\))',
      syntax_acc_6: '(Phương trình hữu tỉ được giữ nguyên để kiểm tra ứng viên)',
      syntax_rejected_title: '✗ Nghiêm ngặt Từ chối (Lỗi Cú pháp)',
      syntax_rej_1: '(Phép nhân ngầm mơ hồ; yêu cầu viết 2*x)',
      syntax_rej_2: '(Nhân ngầm mẫu số; yêu cầu viết 1/(2*x) hoặc (1/2)*x)',
      syntax_rej_3: '(Nhân ngầm ngoặc; yêu cầu viết x*(x+1))',
      syntax_rej_4: '(Số mũ > 2 nằm ngoài phạm vi Giai đoạn P02A)',
      syntax_rej_5: '(Không hỗ trợ đa biến; chỉ chấp nhận đơn biến x)',

      // Footer
      footer_brand: 'Kiến trúc Sản phẩm MKE',
      footer_desc: 'Giai đoạn P02A — Hệ tri thức Toán học Tuyến tính Chuẩn xác. Toàn bộ xử lý tại trình duyệt máy khách, không thu thập dữ liệu mạng bên ngoài.',
      footer_specs_heading: 'Quy chuẩn & Pháp quy',
      footer_baseline_label: 'Quy chuẩn đóng băng:',
      footer_approved_label: 'Mã nguồn phê duyệt:',
      footer_precedence_label: 'Thứ bậc ưu tiên:',
      footer_disclaimer_heading: 'Tuyên bố Bản mẫu',
      footer_disclaimer_desc: 'Lấy cảm hứng từ phong cách WolframAlpha; toàn bộ mã nguồn, biểu tượng SVG, token thiết kế và bố cục đều thuộc bản quyền nguyên bản của MKE. Tất cả kết quả đều được gắn nhãn BẢN MẪU / DỮ LIỆU DEMO.'
    },

    en: {
      // Header & Navigation
      brand_subtitle: 'Math Knowledge Engine',
      brand_home_aria: 'MKE Home',
      prototype_badge: 'UI-00 PROTOTYPE',
      prototype_badge_title: 'Visual Prototype Only (No backend connected)',
      nav_main_aria: 'Main Navigation',
      nav_home: 'Home',
      nav_sample: 'Sample Result',
      nav_syntax: 'Syntax Guide',
      lang_label: 'Language:',
      lang_select_aria: 'Select interface language',
      theme_label: 'Theme:',
      theme_select_aria: 'Select color theme',
      theme_auto: 'Auto (System)',
      theme_light: 'Light',
      theme_dark: 'Dark',

      // Advisory Banner
      banner_tag: 'DEMO / MOCK DATA',
      banner_msg: 'This is a standalone visual prototype. Mathematical outputs are simulated illustrative fixtures; no backend or production solver is connected.',

      // Home Screen — Hero & Search
      hero_title: 'Exact Mathematical Knowledge & Verifiable Computation',
      hero_subtitle: 'Deterministic symbolic reasoning over the real domain \\(\\mathbb{R}\\) with exact rational arithmetic over \\(\\mathbb{Q}\\).',
      input_placeholder: 'Enter equation (e.g., 2*x + 3 = 7, -x^2 = 1, x^0 = 1)...',
      input_aria: 'Mathematical expression input',
      clear_title: 'Clear input',
      clear_aria: 'Clear input',
      compute_btn: 'Compute',
      compute_aria: 'Compute expression',
      keyboard_aria: 'Quick math symbols keyboard',
      kb_hint: 'Insert:',
      sym_mult: '* (explicit mult)',
      chips_aria: 'Representative examples',
      chips_label: 'Examples:',
      chip_syntax_demo: '1/2x = 1 (Syntax Error Demo)',
      chip_syntax_title: 'Demonstrates rejection of ambiguous implicit multiplication',

      // Home Screen — 4 Topic Cards
      topics_section_aria: 'Mathematical domains',
      topics_title: 'Mathematical Topics & Capabilities',
      badge_p02a_active: 'PHASE P02A ACTIVE',
      card_algebra_title: 'Algebra & Linear Equations',
      card_algebra_desc: 'Exact affine linear equations ax + b = 0 over domain \\(\\mathbb{R}\\) with rational coefficients \\(\\mathbb{Q}\\). Handles identities and contradictions.',
      prompt_algebra_identity: '0*x = 0 (Identity over \\(\\mathbb{R}\\))',

      badge_core_active: 'CORE ACTIVE',
      card_rational_title: 'Rational Field Arithmetic',
      card_rational_desc: 'Arbitrary-precision exact arithmetic over \\(\\mathbb{Q}\\). Canonical Euclidean GCD reduction with zero floating-point approximation drift.',
      prompt_rational_domain: 'Domain Exclusions: (x-1)/(x-1)',
      prompt_rational_bigint: 'Large Integers (10^100)',

      badge_planned_r1: 'PLANNED (R1)',
      card_quad_title: 'Quadratics & Factoring',
      card_quad_desc: 'Non-linear equations ax^2 + bx + c = 0, discriminant analysis, completing the square, and independent candidate checking.',
      prompt_quad_candidate: 'x^2 - 4 = 0 (Check Candidate)',
      prompt_quad_factoring: 'Factoring Methods (Planned)',
      prompt_quad_radicals: 'Radical Field Extensions (Planned)',

      badge_planned_r2: 'PLANNED (R2)',
      card_classroom_title: 'Classroom & Document Ingestion',
      card_classroom_desc: 'Step-by-step diagnostic tutoring, student error categorization, and separately gated manual PDF/image math ingestion.',
      prompt_class_tree: 'Step Guidance Tree (Planned)',
      prompt_class_pdf: 'Manual PDF Ingestion (Planned)',
      prompt_class_grade: 'Classroom Roster Grading (Planned)',

      // Result Screen
      btn_back_home: '← Back to Home',
      active_query_label: 'Active Query:',
      card_input_title: 'Input Interpretation',
      status_syntax_valid: 'SYNTACTICALLY VALID',
      status_syntax_invalid: 'SYNTAX ERROR (REJECTED)',
      meta_grammar_label: 'Grammar Standard:',
      meta_mult_label: 'Multiplication:',
      meta_mult_val: 'Explicit (* confirmed)',
      meta_mult_invalid_val: 'Ambiguous implicit multiplication detected',
      meta_ast_nodes_label: 'AST Nodes:',
      meta_ast_nodes_val: '7 nodes preserved',
      ast_summary: 'View Parsed AST Structure',

      card_solution_title: 'Exact Solution',
      methods_aria: 'Solution methods',
      tab_linear_algebra: 'Linear Field Algebra',
      tab_factoring_planned: 'Factoring (Planned)',
      tab_graphic_planned: 'Graphic Form (Planned)',
      tab_planned_r1_title: 'Planned for Release 1',
      sol_domain_tag: 'Exact Rational in \\(\\mathbb{Q}\\)',
      trace_title: 'Deterministic Step-by-Step Derivation',

      card_domain_title: 'Domain & Verification Evidence',
      badge_mock_specimen: 'DEMO / MOCK SPECIMEN',
      tile_eq_domain: 'Equation Domain',
      val_eq_domain: 'Real Numbers \\(\\mathbb{R}\\)',
      tile_domain_constraints: 'Original Domain Constraints',
      tile_candidate_check: 'Candidate Check',
      tag_specimen_notice: 'SIMULATED INTERFACE SPECIMEN (DEMO)',
      msg_specimen_disclaimer: 'This section is a visual mockup demonstration. No cryptographic hash is calculated or attested by this visual prototype. Production cryptographic signing is planned for future milestones.',

      // Syntax Guide Screen
      syntax_guide_title: 'MKE Phase P02A Syntax Specification',
      syntax_guide_lead: 'MKE enforces strict mathematical explicit syntax to prevent ambiguity and silent parsing misinterpretations.',
      syntax_accepted_title: '✓ Accepted Syntax',
      syntax_acc_1: '(Explicit multiplication with *)',
      syntax_acc_2: '(Parsed as -(x^2))',
      syntax_acc_3: '(Grouped negative base)',
      syntax_acc_4: '(Preserves power node; evaluated over original domain)',
      syntax_acc_5: '(Identity equation; solution domain \\(\\mathbb{R}\\))',
      syntax_acc_6: '(Rational equation preserved for candidate verification)',
      syntax_rejected_title: '✗ Strictly Rejected (Syntax Errors)',
      syntax_rej_1: '(Ambiguous implicit multiplication; use 2*x)',
      syntax_rej_2: '(Implicit multiplication; use 1/(2*x) or (1/2)*x)',
      syntax_rej_3: '(Implicit multiplication; use x*(x+1))',
      syntax_rej_4: '(Exponent > 2 out of scope in Phase P02A)',
      syntax_rej_5: '(Multi-variable unsupported; single variable x only)',

      // Footer
      footer_brand: 'MKE Product Architecture',
      footer_desc: 'Phase P02A — Exact Linear Mathematical Knowledge Engine. All client-side processing, zero external network telemetry.',
      footer_specs_heading: 'Specifications & Governance',
      footer_baseline_label: 'Frozen Baseline:',
      footer_approved_label: 'Approved Product:',
      footer_precedence_label: 'Precedence:',
      footer_disclaimer_heading: 'Prototype Disclaimer',
      footer_disclaimer_desc: 'WolframAlpha inspired aesthetic; all code, SVG icons, tokens, and layouts are original to MKE. All results are labeled DEMO / MOCK DATA.'
    }
  };

  // Helper for lookup with explicit fallback hierarchy: current -> 'vi' -> 'en' -> key
  function t(key, lang) {
    const targetLang = lang || currentLanguage;
    if (I18N[targetLang] && I18N[targetLang][key] !== undefined) {
      return I18N[targetLang][key];
    }
    if (I18N.vi && I18N.vi[key] !== undefined) {
      return I18N.vi[key];
    }
    if (I18N.en && I18N.en[key] !== undefined) {
      return I18N.en[key];
    }
    return key;
  }

  // ==========================================================================
  // Language Management (Vietnamese default, English supported)
  // ==========================================================================
  const LANG_STORAGE_KEY = 'mke_language_preference';
  let currentLanguage = 'vi';
  const langSelect = document.getElementById('lang-select');

  function applyLanguage(lang, syncUrl) {
    if (lang !== 'vi' && lang !== 'en') {
      lang = 'vi';
    }
    currentLanguage = lang;
    document.documentElement.setAttribute('lang', lang);

    if (langSelect) {
      langSelect.value = lang;
    }

    // Apply textContent to all elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      if (key) {
        el.textContent = t(key, lang);
      }
    });

    // Apply attribute translations for data-i18n-attr (e.g. "placeholder:input_placeholder,title:clear_title")
    document.querySelectorAll('[data-i18n-attr]').forEach((el) => {
      const spec = el.getAttribute('data-i18n-attr');
      if (!spec) return;
      spec.split(',').forEach((pair) => {
        const parts = pair.split(':');
        if (parts.length === 2) {
          const attr = parts[0].trim();
          const key = parts[1].trim();
          el.setAttribute(attr, t(key, lang));
        }
      });
    });

    // If currently viewing the result screen, re-render fixture to update step descriptions and candidate checks
    if (screens.result && screens.result.classList.contains('active')) {
      renderActiveResult();
    }

    if (syncUrl) {
      try {
        const url = new URL(window.location.href);
        url.searchParams.set('lang', lang);
        window.history.replaceState({}, '', url.toString());
      } catch (e) {
        // Fallback gracefully if history API is restricted in sandboxes
      }
    }
  }

  function setLanguage(newLang) {
    if (newLang !== 'vi' && newLang !== 'en') return;
    localStorage.setItem(LANG_STORAGE_KEY, newLang);
    applyLanguage(newLang, true);
  }

  function initLanguage() {
    const urlParams = new URLSearchParams(window.location.search);
    const langParam = urlParams.get('lang');
    let initialLang = 'vi';

    if (langParam === 'vi' || langParam === 'en') {
      initialLang = langParam;
    } else {
      const saved = localStorage.getItem(LANG_STORAGE_KEY);
      if (saved === 'vi' || saved === 'en') {
        initialLang = saved;
      }
    }

    applyLanguage(initialLang, false);

    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        setLanguage(e.target.value);
      });
    }
  }

  // ==========================================================================
  // Theme Management (Light, Dark, Auto)
  // ==========================================================================
  const THEME_STORAGE_KEY = 'mke_visual_theme_preference';
  const htmlRoot = document.documentElement;
  const themeSelect = document.getElementById('theme-select');

  function getSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  function applyTheme(preference) {
    const effectiveTheme = preference === 'auto' ? getSystemTheme() : preference;
    htmlRoot.setAttribute('data-theme', effectiveTheme);
    if (themeSelect) {
      themeSelect.value = preference;
    }
  }

  function initTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get('theme');
    const saved = themeParam || localStorage.getItem(THEME_STORAGE_KEY) || 'auto';
    applyTheme(saved);

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const currentPref = localStorage.getItem(THEME_STORAGE_KEY) || 'auto';
        if (currentPref === 'auto') {
          applyTheme('auto');
        }
      });
    }

    if (themeSelect) {
      themeSelect.addEventListener('change', (e) => {
        const newPref = e.target.value;
        localStorage.setItem(THEME_STORAGE_KEY, newPref);
        applyTheme(newPref);
      });
    }
  }

  // ==========================================================================
  // Screen Navigation
  // ==========================================================================
  const screens = {
    home: document.getElementById('screen-home'),
    result: document.getElementById('screen-result'),
    syntax: document.getElementById('screen-syntax')
  };

  const navBtns = {
    home: document.getElementById('nav-home'),
    result: document.getElementById('nav-demo-result'),
    syntax: document.getElementById('nav-syntax')
  };

  function switchScreen(screenKey) {
    Object.keys(screens).forEach((key) => {
      if (screens[key]) {
        screens[key].classList.toggle('active', key === screenKey);
      }
    });

    Object.keys(navBtns).forEach((key) => {
      if (navBtns[key]) {
        navBtns[key].classList.toggle('active', key === screenKey);
      }
    });

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ==========================================================================
  // Input and Quick Math Toolbar
  // ==========================================================================
  const mathInput = document.getElementById('math-input');
  const btnClear = document.getElementById('btn-clear');
  const searchForm = document.getElementById('search-form');

  function insertSymbol(sym) {
    if (!mathInput) return;
    const start = mathInput.selectionStart || mathInput.value.length;
    const end = mathInput.selectionEnd || mathInput.value.length;
    const current = mathInput.value;

    if (sym === '( )') {
      mathInput.value = current.substring(0, start) + '()' + current.substring(end);
      mathInput.setSelectionRange(start + 1, start + 1);
    } else {
      mathInput.value = current.substring(0, start) + sym + current.substring(end);
      mathInput.setSelectionRange(start + sym.length, start + sym.length);
    }
    mathInput.focus();
  }

  // ==========================================================================
  // Mock Result Calculation Fixtures (Client-Side Illustrative Demo Only)
  // Mathematical representations remain strictly untranslated.
  // Explanatory texts adapt dynamically to chosen language.
  // ==========================================================================
  let activeQueryString = '2*x + 3 = 7';

  const MOCK_FIXTURES = {
    '2*x + 3 = 7': {
      mathDisplay: '2x + 3 = 7',
      ast: `Equation(
  left=BinaryOp("+",
    left=BinaryOp("*", left=IntegerLiteral(2), right=Variable("x")),
    right=IntegerLiteral(3)),
  right=IntegerLiteral(7)
)`,
      solutionVar: 'x',
      solutionVal: '2',
      i18n: {
        vi: {
          domainConstraints: 'Không có (Không có biến ở mẫu số)',
          candidateCheck: '|L(2) - R(2)| = 0 (Chính xác)',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Chuyển vế hằng số bằng cách trừ 3 ở cả hai vế:',
              math: '2*x + 3 - 3 = 7 - 3  ==>  2*x = 4'
            },
            {
              num: 'Bước 2',
              desc: 'Nhân với nghịch đảo của hệ số a=2 trong trường số hữu tỉ Q:',
              math: 'x = 4 / 2 = 2'
            }
          ]
        },
        en: {
          domainConstraints: 'None (No variable denominators)',
          candidateCheck: '|L(2) - R(2)| = 0 (Exact)',
          steps: [
            {
              num: 'Step 1',
              desc: 'Isolate variable terms by subtracting constant 3 from both sides:',
              math: '2*x + 3 - 3 = 7 - 3  ==>  2*x = 4'
            },
            {
              num: 'Step 2',
              desc: 'Apply multiplicative inverse of coefficient a=2 in field Q:',
              math: 'x = 4 / 2 = 2'
            }
          ]
        }
      }
    },

    '-x^2 = 1': {
      mathDisplay: '-x^2 = 1  [Parsed as -(x^2) = 1]',
      ast: `Equation(
  left=UnaryOp("-",
    operand=Power(base=Variable("x"), exponent=IntegerLiteral(2))),
  right=IntegerLiteral(1)
)`,
      solutionVar: 'Status',
      i18n: {
        vi: {
          solutionVal: 'Vô nghiệm thực (Tập rỗng)',
          domainConstraints: 'x thuộc R (Bậc hai được bảo toàn trong AST)',
          candidateCheck: 'Đa thức bậc 2 (Bộ giải SOLVE từ chối xử lý trong Giai đoạn P02A)',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Kiểm tra thứ tự ưu tiên: Dấu trừ một ngôi liên kết bên ngoài nút lũy thừa:',
              math: '-x^2  ==>  -(x^2)'
            },
            {
              num: 'Bước 2',
              desc: 'Nhân cả hai vế với -1:',
              math: 'x^2 = -1  (Không có nghiệm trong trường số thực R)'
            }
          ]
        },
        en: {
          solutionVal: 'No Real Roots (EmptySet)',
          domainConstraints: 'x in R (Quadratic power retained in AST)',
          candidateCheck: 'Degree 2 polynomial (SOLVE abstains in Phase P02A)',
          steps: [
            {
              num: 'Step 1',
              desc: 'Precedence Verification: Unary minus binds outside power node:',
              math: '-x^2  ==>  -(x^2)'
            },
            {
              num: 'Step 2',
              desc: 'Multiply both sides by -1:',
              math: 'x^2 = -1  (No solution in Real field R)'
            }
          ]
        }
      }
    },

    '(-x)^2 = 1': {
      mathDisplay: '(-x)^2 = 1  [Grouped base (-x)]',
      ast: `Equation(
  left=Power(
    base=Group(inner=UnaryOp("-", operand=Variable("x"))),
    exponent=IntegerLiteral(2)),
  right=IntegerLiteral(1)
)`,
      solutionVar: 'Roots',
      solutionVal: 'x = 1, x = -1',
      i18n: {
        vi: {
          domainConstraints: 'Miền số thực R',
          candidateCheck: 'Cả hai nghiệm đều được kiểm chứng chính xác trong bộ kiểm tra ứng viên',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Bảo toàn cơ số âm được nhóm (-x):',
              math: '(-x)^2 = x^2 = 1'
            },
            {
              num: 'Bước 2',
              desc: 'Xác định các nghiệm trên trường số hữu tỉ Q:',
              math: 'x = 1  hoặc  x = -1'
            }
          ]
        },
        en: {
          domainConstraints: 'Real Domain R',
          candidateCheck: 'Both roots verify exactly in candidate checker',
          steps: [
            {
              num: 'Step 1',
              desc: 'Preserve grouped negative base (-x):',
              math: '(-x)^2 = x^2 = 1'
            },
            {
              num: 'Step 2',
              desc: 'Evaluate roots over field Q:',
              math: 'x = 1  or  x = -1'
            }
          ]
        }
      }
    },

    'x^0 = 1': {
      mathDisplay: 'x^0 = 1',
      ast: `Equation(
  left=Power(base=Variable("x"), exponent=IntegerLiteral(0)),
  right=IntegerLiteral(1)
)`,
      solutionVar: 'Domain',
      i18n: {
        vi: {
          solutionVal: 'R \\ {0} (Tất cả số thực khác 0)',
          domainConstraints: 'x != 0 (0^0 không xác định trên trường số thực)',
          candidateCheck: 'Ứng viên x=2 HỢP LỆ (2^0=1); ứng viên x=0 KHÔNG HỢP LỆ (0^0)',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Đánh giá theo định nghĩa lũy thừa biến:',
              math: 'x^0 = 1  với mọi x != 0'
            },
            {
              num: 'Bước 2',
              desc: 'Loại trừ điểm kỳ dị bất định:',
              math: '0^0 không xác định về mặt toán học'
            }
          ]
        },
        en: {
          solutionVal: 'R \\ {0} (All non-zero reals)',
          domainConstraints: 'x != 0 (0^0 is undefined in Real field)',
          candidateCheck: 'Candidate x=2 is VALID (2^0=1); candidate x=0 is INVALID (0^0)',
          steps: [
            {
              num: 'Step 1',
              desc: 'Evaluate base exponent definition:',
              math: 'x^0 = 1  for all x != 0'
            },
            {
              num: 'Step 2',
              desc: 'Exclude indeterminate singularity:',
              math: '0^0 is mathematically UNDEFINED'
            }
          ]
        }
      }
    },

    '0*x = 0': {
      mathDisplay: '0*x = 0',
      ast: `Equation(
  left=BinaryOp("*", left=IntegerLiteral(0), right=Variable("x")),
  right=IntegerLiteral(0)
)`,
      solutionVar: 'DomainSet',
      i18n: {
        vi: {
          solutionVal: 'R (Đồng nhất thức trên miền số thực)',
          domainConstraints: 'Xác định tầm thường với mọi x thuộc R',
          candidateCheck: 'Mọi ứng viên thuộc Q đều thỏa mãn đẳng thức',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Đánh giá các hệ số tuyến tính a=0, b=0:',
              math: '0*x + 0 = 0  ==>  0 = 0  (Đồng nhất thức)'
            }
          ]
        },
        en: {
          solutionVal: 'R (Identity over Real Domain)',
          domainConstraints: 'Trivially defined for all x in R',
          candidateCheck: 'Any candidate in Q satisfies equality',
          steps: [
            {
              num: 'Step 1',
              desc: 'Evaluate linear coefficients a=0, b=0:',
              math: '0*x + 0 = 0  ==>  0 = 0  (Identity)'
            }
          ]
        }
      }
    },

    '(x-1)/(x-1) = 1': {
      mathDisplay: '(x-1)/(x-1) = 1',
      ast: `Equation(
  left=BinaryOp("/",
    left=Group(inner=BinaryOp("-", left=Variable("x"), right=IntegerLiteral(1))),
    right=Group(inner=BinaryOp("-", left=Variable("x"), right=IntegerLiteral(1)))),
  right=IntegerLiteral(1)
)`,
      solutionVar: 'DomainSet',
      i18n: {
        vi: {
          solutionVal: 'R \\ {1} (Mọi x != 1)',
          domainConstraints: 'x != 1 (Phép chia cho 0 bị loại trừ khỏi miền ban đầu)',
          candidateCheck: 'Ứng viên x=1 kích hoạt lỗi DOMAIN_ERROR_DIVISION_BY_ZERO',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Trích xuất ràng buộc miền từ mẫu số chưa rút gọn:',
              math: 'Mẫu số (x - 1) != 0  ==>  x != 1'
            },
            {
              num: 'Bước 2',
              desc: 'Với mọi x != 1, thương số rút gọn thành 1:',
              math: '1 = 1  với mọi x thuộc R \\ {1}'
            }
          ]
        },
        en: {
          solutionVal: 'R \\ {1} (All x != 1)',
          domainConstraints: 'x != 1 (Division by zero excluded from original domain)',
          candidateCheck: 'Candidate x=1 triggers DOMAIN_ERROR_DIVISION_BY_ZERO',
          steps: [
            {
              num: 'Step 1',
              desc: 'Extract domain restriction from unreduced denominator:',
              math: 'Denominator (x - 1) != 0  ==>  x != 1'
            },
            {
              num: 'Step 2',
              desc: 'For all x != 1, quotient simplifies to 1:',
              math: '1 = 1  for all x in R \\ {1}'
            }
          ]
        }
      }
    }
  };

  function renderActiveResult() {
    const trimmed = activeQueryString.trim();
    const resultQueryText = document.getElementById('result-query-text');
    const mathDisplay = document.getElementById('res-math-display');
    const astJson = document.getElementById('res-ast-json');
    const solutionVar = document.getElementById('res-solution-var');
    const solutionVal = document.getElementById('res-solution-val');
    const domainConstraints = document.getElementById('res-domain-constraints');
    const candidateCheck = document.getElementById('res-candidate-check');
    const stepsList = document.getElementById('res-steps-list');
    const syntaxStatus = document.getElementById('res-syntax-status');
    const metaMult = document.getElementById('res-meta-mult');

    if (resultQueryText) resultQueryText.textContent = trimmed;

    // Check if input triggers explicit-multiplication error demo
    if (trimmed.includes('2x') || trimmed.includes('1/2x') || trimmed.includes('x(')) {
      if (syntaxStatus) {
        syntaxStatus.textContent = t('status_syntax_invalid');
        syntaxStatus.className = 'syntax-status status-invalid';
      }
      if (metaMult) {
        metaMult.textContent = t('meta_mult_invalid_val');
      }
      if (mathDisplay) mathDisplay.textContent = trimmed;
      if (astJson) {
        astJson.textContent = currentLanguage === 'vi'
          ? `[LỖI CÚ PHÁP: ImplicitMultiplicationError]\nPhép nhân ngầm mơ hồ bị từ chối; hãy sử dụng dấu '*' tường minh (ví dụ: '2*x' thay vì '2x').\nVị trí nguồn: các token liền kề.`
          : `[SYNTAX ERROR: ImplicitMultiplicationError]\nAmbiguous implicit multiplication is rejected; use explicit '*' (e.g. '2*x' instead of '2x').\nSource Span: position of adjacent tokens.`;
      }
      if (solutionVar) solutionVar.textContent = 'Status';
      if (solutionVal) solutionVal.textContent = currentLanguage === 'vi' ? 'Lỗi Cú pháp (Từ chối)' : 'Syntax Error (Rejected)';
      if (domainConstraints) domainConstraints.textContent = currentLanguage === 'vi' ? 'Dừng phân tích trước khi chuyển vào bộ giải' : 'Parsing halted before solver';
      if (candidateCheck) candidateCheck.textContent = currentLanguage === 'vi' ? 'Không kiểm tra ứng viên khi cú pháp bị từ chối' : 'No candidate checking on syntax rejection';
      
      if (stepsList) {
        stepsList.innerHTML = '';
        const item = document.createElement('li');
        item.className = 'step-item';
        item.style.borderLeftColor = '#ef4444';

        const stepNum = document.createElement('div');
        stepNum.className = 'step-num';
        stepNum.style.color = '#ef4444';
        stepNum.textContent = currentLanguage === 'vi' ? 'Lỗi Cú pháp' : 'Syntax Error';

        const stepDesc = document.createElement('div');
        stepDesc.className = 'step-desc';
        stepDesc.textContent = currentLanguage === 'vi'
          ? 'MKE yêu cầu phép nhân tường minh để loại trừ hoàn toàn sự mơ hồ toán học:'
          : 'MKE requires explicit multiplication to prevent mathematical ambiguity:';

        const stepMath = document.createElement('div');
        stepMath.className = 'step-math';
        stepMath.textContent = currentLanguage === 'vi'
          ? 'Vui lòng viết rõ ràng: 2*x hoặc (1/2)*x'
          : 'Please write explicitly: 2*x or (1/2)*x';

        item.appendChild(stepNum);
        item.appendChild(stepDesc);
        item.appendChild(stepMath);
        stepsList.appendChild(item);
      }
      return;
    }

    // Normal valid input syntax
    if (syntaxStatus) {
      syntaxStatus.textContent = t('status_syntax_valid');
      syntaxStatus.className = 'syntax-status status-valid';
    }
    if (metaMult) {
      metaMult.textContent = t('meta_mult_val');
    }

    const fixture = MOCK_FIXTURES[trimmed] || {
      mathDisplay: trimmed,
      ast: `Equation(
  left=ParsedExpression("${trimmed.split('=')[0] || ''}"),
  right=ParsedExpression("${trimmed.split('=')[1] || ''}")
)`,
      solutionVar: 'x',
      solutionVal: '2',
      i18n: {
        vi: {
          solutionVal: 'Nghiệm minh họa (Demo)',
          domainConstraints: 'Miền thực R với hệ số thuộc Q',
          candidateCheck: 'Đạt điều kiện kiểm tra minh họa',
          steps: [
            {
              num: 'Bước 1',
              desc: 'Biến đổi chuẩn tắc phục vụ minh họa:',
              math: trimmed
            }
          ]
        },
        en: {
          solutionVal: 'Sample Exact Solution (Demo)',
          domainConstraints: 'Domain R with coefficients in Q',
          candidateCheck: 'Simulated verification check passed',
          steps: [
            {
              num: 'Step 1',
              desc: 'Standard canonical reduction for demonstration:',
              math: trimmed
            }
          ]
        }
      }
    };

    const localized = (fixture.i18n && fixture.i18n[currentLanguage])
      || (fixture.i18n && fixture.i18n.vi)
      || (fixture.i18n && fixture.i18n.en)
      || {};

    if (mathDisplay) mathDisplay.textContent = fixture.mathDisplay;
    if (astJson) astJson.textContent = fixture.ast;
    if (solutionVar) solutionVar.textContent = fixture.solutionVar || 'x';
    if (solutionVal) solutionVal.textContent = localized.solutionVal || fixture.solutionVal || '2';
    if (domainConstraints) domainConstraints.textContent = localized.domainConstraints || '';
    if (candidateCheck) candidateCheck.textContent = localized.candidateCheck || '';

    if (stepsList) {
      stepsList.innerHTML = '';
      const steps = localized.steps || [];
      steps.forEach((s) => {
        const item = document.createElement('li');
        item.className = 'step-item';

        const stepNum = document.createElement('div');
        stepNum.className = 'step-num';
        stepNum.textContent = s.num;

        const stepDesc = document.createElement('div');
        stepDesc.className = 'step-desc';
        stepDesc.textContent = s.desc;

        const stepMath = document.createElement('div');
        stepMath.className = 'step-math';
        stepMath.textContent = s.math;

        item.appendChild(stepNum);
        item.appendChild(stepDesc);
        item.appendChild(stepMath);
        stepsList.appendChild(item);
      });
    }
  }

  function displayResult(query) {
    activeQueryString = query;
    renderActiveResult();
    switchScreen('result');
  }

  // ==========================================================================
  // Event Listeners Setup
  // ==========================================================================
  function initEvents() {
    // Navigation
    if (navBtns.home) navBtns.home.addEventListener('click', () => switchScreen('home'));
    if (navBtns.result) navBtns.result.addEventListener('click', () => displayResult(mathInput ? mathInput.value : '2*x + 3 = 7'));
    if (navBtns.syntax) navBtns.syntax.addEventListener('click', () => switchScreen('syntax'));
    const brandLogo = document.getElementById('brand-logo');
    if (brandLogo) {
      brandLogo.addEventListener('click', () => switchScreen('home'));
      brandLogo.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          switchScreen('home');
        }
      });
    }

    const btnBack = document.getElementById('btn-back-home');
    if (btnBack) btnBack.addEventListener('click', () => switchScreen('home'));

    // Input actions
    if (btnClear) {
      btnClear.addEventListener('click', () => {
        if (mathInput) {
          mathInput.value = '';
          mathInput.focus();
        }
      });
    }

    // Keyboard toolbar buttons
    document.querySelectorAll('.sym-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        insertSymbol(btn.getAttribute('data-sym') || '');
      });
    });

    // Form submit / Compute button
    if (searchForm) {
      searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (mathInput && mathInput.value.trim()) {
          displayResult(mathInput.value);
        }
      });
    }

    // Example prompt chips and prompt links
    document.querySelectorAll('.chip, .prompt-link:not(.disabled)').forEach((btn) => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        if (query) {
          if (mathInput) mathInput.value = query;
          displayResult(query);
        }
      });
    });
  }

  // Initialize on DOM load
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initLanguage();
    initEvents();

    const urlParams = new URLSearchParams(window.location.search);
    const viewParam = urlParams.get('view');
    const queryParam = urlParams.get('query');
    if (viewParam === 'result') {
      displayResult(queryParam || (mathInput ? mathInput.value : '2*x + 3 = 7'));
    } else if (viewParam === 'syntax') {
      switchScreen('syntax');
    }
  });
})();
