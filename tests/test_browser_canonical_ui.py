"""
MKE PRODUCT-03A-R3: Canonical UI Automated Browser Verification Suite.

Tests genuine browser interactions, offline KaTeX mathematical typesetting,
fail-closed backend disconnection semantics (ZERO fake results/proofs),
honest verification badges, bilingual switching, and theme transitions.
Captures screenshots to evidence/ui_r3/screenshots/.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mke_product.cas.demo_server import MKEProductHTTPRequestHandler

SCREENSHOTS_DIR = REPO_ROOT / "evidence" / "ui_r4" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class TestCanonicalUIBrowserSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Start live background server on loopback ephemeral port with multithreading
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MKEProductHTTPRequestHandler)
        cls.host, cls.port = cls.server.server_address
        cls.base_url = f"http://{cls.host}:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

        # 2. Start Selenium Headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1366,850")
        chrome_options.add_argument("--disable-dev-shm-usage")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(4.0)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver"):
            cls.driver.quit()
        if hasattr(cls, "server"):
            cls.server.shutdown()
            cls.server.server_close()
            cls.server_thread.join(timeout=1.0)

    def _save_screenshot(self, name: str) -> str:
        filepath = SCREENSHOTS_DIR / f"{name}.png"
        self.driver.save_screenshot(str(filepath))
        return str(filepath)

    def _wait_for_math_render(self, timeout: float = 3.0):
        time.sleep(0.4)
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "katex")) > 0
            )
        except Exception:
            pass

    def _submit_query(self, query: str):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")
        math_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.ID, "math-input"))
        )
        math_input.clear()
        math_input.send_keys(query)
        self.driver.find_element(By.CLASS_NAME, "compute-btn").click()
        WebDriverWait(self.driver, 5.0).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#screen-result.active"))
        )
        time.sleep(0.5)

    # -------------------------------------------------------------------------
    # Scenario 1: Load Original Homepage
    # -------------------------------------------------------------------------
    def test_01_load_homepage(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")
        self._wait_for_math_render()

        title = self.driver.title
        self.assertIn("Math Knowledge Engine", title)

        # Verify Header right group
        header_group = self.driver.find_element(By.CLASS_NAME, "header-right-group")
        self.assertTrue(header_group.is_displayed())

        # Verify Search input
        math_input = self.driver.find_element(By.ID, "math-input")
        self.assertTrue(math_input.is_displayed())

        # Verify Topic grid
        topic_grid = self.driver.find_element(By.CLASS_NAME, "topic-4col-grid")
        self.assertTrue(topic_grid.is_displayed())

        # Verify live banner
        banner = self.driver.find_element(By.ID, "app-connection-banner")
        self.assertTrue(banner.is_displayed())
        self.assertIn("banner-connected", banner.get_attribute("class"))

        self._save_screenshot("01_homepage_initial")

    # -------------------------------------------------------------------------
    # Scenario 2: Solve Linear Equation (Native MKE Engine)
    # -------------------------------------------------------------------------
    def test_02_solve_linear_equation(self):
        self._submit_query("2*x + 3 = 7")
        self._wait_for_math_render()

        engine_badge = self.driver.find_element(By.ID, "res-engine-badge").text
        self.assertEqual(engine_badge, "mke_native_v1")

        sol_box_text = self.driver.find_element(By.ID, "res-solution-box").text
        self.assertIn("2", sol_box_text)

        # Check step items
        step_items = self.driver.find_elements(By.CLASS_NAME, "step-item")
        self.assertGreaterEqual(len(step_items), 2)

        # Check KaTeX presence
        katex_math = self.driver.find_elements(By.CSS_SELECTOR, "#res-solution-val .katex")
        self.assertGreaterEqual(len(katex_math), 1)

        # Check deterministic verification badge
        cert_badge = self.driver.find_element(By.ID, "res-cert-badge")
        self.assertIn("CHỨNG THỰC TẤT ĐỊNH", cert_badge.text)
        self.assertIn("status-valid-cert", cert_badge.get_attribute("class"))

        self._save_screenshot("02_solve_linear_mke_native")

    # -------------------------------------------------------------------------
    # Scenario 3: Solve Quadratic Equation
    # -------------------------------------------------------------------------
    def test_03_solve_quadratic_equation(self):
        self._submit_query("x^2 - 5*x + 6 = 0")
        WebDriverWait(self.driver, 5.0).until(
            lambda d: "3" in d.find_element(By.ID, "res-solution-box").text
        )
        self._wait_for_math_render()

        engine_badge = self.driver.find_element(By.ID, "res-engine-badge").text
        self.assertIn(engine_badge, ["mke_native_v1", "sympy_cas_v0"])

        sol_box_text = self.driver.find_element(By.ID, "res-solution-box").text
        self.assertTrue("2" in sol_box_text and "3" in sol_box_text)

        self._save_screenshot("03_solve_quadratic")

    # -------------------------------------------------------------------------
    # Scenario 4: Differentiate Polynomial (SymPy CAS)
    # -------------------------------------------------------------------------
    def test_04_differentiate_polynomial(self):
        self._submit_query("3*x^3 - 5*x + 2")

        # Switch to Differentiate tab
        tab_diff = self.driver.find_element(By.ID, "tab-diff")
        tab_diff.click()
        time.sleep(0.6)
        self._wait_for_math_render()

        sol_box_text = self.driver.find_element(By.ID, "res-solution-box").text
        self.assertTrue("9" in sol_box_text and ("5" in sol_box_text or "x" in sol_box_text))

        engine_badge = self.driver.find_element(By.ID, "res-engine-badge").text
        self.assertEqual(engine_badge, "sympy_cas_v0")

        self._save_screenshot("04_differentiation_result")

    # -------------------------------------------------------------------------
    # Scenario 5: Integrate Polynomial (SymPy CAS)
    # -------------------------------------------------------------------------
    def test_05_integrate_polynomial(self):
        self._submit_query("x^2 + 2*x")

        # Switch to Integrate tab
        tab_int = self.driver.find_element(By.ID, "tab-integrate")
        tab_int.click()
        time.sleep(0.6)
        self._wait_for_math_render()

        sol_box_text = self.driver.find_element(By.ID, "res-solution-box").text
        self.assertTrue("3" in sol_box_text or "x" in sol_box_text)

        engine_badge = self.driver.find_element(By.ID, "res-engine-badge").text
        self.assertEqual(engine_badge, "sympy_cas_v0")

        self._save_screenshot("05_integration_result")

    # -------------------------------------------------------------------------
    # Scenario 6: Render 2D Graph (SVG Cartesian)
    # -------------------------------------------------------------------------
    def test_06_render_2d_graph(self):
        self._submit_query("x^2 - 4")

        tab_plot = self.driver.find_element(By.ID, "tab-plot")
        tab_plot.click()
        time.sleep(0.6)

        plot_wrapper = self.driver.find_element(By.ID, "res-plot-wrapper")
        self.assertTrue(plot_wrapper.is_displayed())

        svg_plots = self.driver.find_elements(By.CSS_SELECTOR, ".mke-plot-svg path")
        self.assertGreaterEqual(len(svg_plots), 1)

        self._save_screenshot("06_plot_2d_cartesian")

    # -------------------------------------------------------------------------
    # Scenario 7: Domain Exclusion Preservation
    # -------------------------------------------------------------------------
    def test_07_domain_exclusion(self):
        self._submit_query("(x-1)/(x-1) = 1")
        self._wait_for_math_render()

        domain_constraints = self.driver.find_element(By.ID, "res-domain-constraints").text
        self.assertTrue("x" in domain_constraints and "1" in domain_constraints)

        self._save_screenshot("07_domain_exclusion_check")

    # -------------------------------------------------------------------------
    # Scenario 8: Bilingual Localization (VN <-> EN)
    # -------------------------------------------------------------------------
    def test_08_bilingual_localization(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")

        # Open Popover
        btn_settings = self.driver.find_element(By.ID, "btn-settings")
        btn_settings.click()
        time.sleep(0.25)

        # Open Language Accordion Section
        header_lang = self.driver.find_element(By.ID, "header-language-toggle")
        self.driver.execute_script("arguments[0].click();", header_lang)
        time.sleep(0.25)

        # Switch to English
        opt_en = self.driver.find_element(By.ID, "opt-lang-en")
        self.driver.execute_script("arguments[0].click();", opt_en)
        time.sleep(0.3)

        self.assertEqual(self.driver.find_element(By.TAG_NAME, "html").get_attribute("lang"), "en")
        nav_home = self.driver.find_element(By.ID, "nav-home").text
        self.assertEqual(nav_home, "Home")

        self._save_screenshot("08_english_localization")

        # Switch back to Vietnamese
        opt_vi = self.driver.find_element(By.ID, "opt-lang-vi")
        self.driver.execute_script("arguments[0].click();", opt_vi)
        time.sleep(0.3)

        self.assertEqual(self.driver.find_element(By.TAG_NAME, "html").get_attribute("lang"), "vi")
        nav_home_vi = self.driver.find_element(By.ID, "nav-home").text
        self.assertEqual(nav_home_vi, "Trang chủ")

    # -------------------------------------------------------------------------
    # Scenario 9: Theme Transitions (Light <-> Dark)
    # -------------------------------------------------------------------------
    def test_09_theme_transitions(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")

        btn_settings = self.driver.find_element(By.ID, "btn-settings")
        btn_settings.click()
        time.sleep(0.25)

        opt_dark = self.driver.find_element(By.ID, "opt-theme-dark")
        self.driver.execute_script("arguments[0].click();", opt_dark)
        time.sleep(0.3)

        html_elem = self.driver.find_element(By.TAG_NAME, "html")
        self.assertEqual(html_elem.get_attribute("data-theme"), "dark")

        self._save_screenshot("09_charcoal_dark_theme")

        # Switch back to light
        opt_light = self.driver.find_element(By.ID, "opt-theme-light")
        self.driver.execute_script("arguments[0].click();", opt_light)
        time.sleep(0.3)

        self.assertEqual(html_elem.get_attribute("data-theme"), "light")

    # -------------------------------------------------------------------------
    # Scenario 10-12: Disconnection Handling: Fail-Closed, ZERO Fake Results/Proofs
    # -------------------------------------------------------------------------
    def test_10_disconnection_fail_closed_zero_fake_results(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")

        # Inject fetch failure simulator into window to simulate server offline
        self.driver.execute_script("""
            window.fetch = function() {
                return Promise.reject(new TypeError('Failed to fetch (Backend Server Disconnected)'));
            };
        """)

        math_input = self.driver.find_element(By.ID, "math-input")
        math_input.clear()
        math_input.send_keys("5*x - 10 = 0")
        self.driver.find_element(By.CLASS_NAME, "compute-btn").click()

        WebDriverWait(self.driver, 5.0).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#screen-result.active"))
        )
        time.sleep(0.3)

        # 1. Verify status is CONNECTION_ERROR
        syntax_status = self.driver.find_element(By.ID, "res-syntax-status").text
        self.assertTrue("LỖI KẾT NỐI" in syntax_status or "CONNECTION" in syntax_status)

        # 2. Verify NO fake mathematical answer is displayed
        sol_box_text = self.driver.find_element(By.ID, "res-solution-box").text
        self.assertNotIn("x = 2", sol_box_text)
        self.assertTrue("Không thể kết nối" in sol_box_text or "Unable to reach" in sol_box_text)

        # 3. Verify NO fake proof steps are rendered
        step_trace = self.driver.find_element(By.ID, "res-step-trace")
        self.assertFalse(step_trace.is_displayed())

        # 4. Verify retry button exists
        retry_btn = self.driver.find_element(By.ID, "btn-retry-exec")
        self.assertTrue(retry_btn.is_displayed())

        # 5. Verify preserved input
        query_text = self.driver.find_element(By.ID, "result-query-text").text
        self.assertEqual(query_text, "5*x - 10 = 0")

        self._save_screenshot("10_backend_disconnect_fail_closed")

    # -------------------------------------------------------------------------
    # Scenario 13: KaTeX Mathematical Typography Verification
    # -------------------------------------------------------------------------
    def test_13_katex_typography(self):
        self._submit_query("x^2 + 2*x + 1 = 0")
        self._wait_for_math_render()

        # Check KaTeX elements in solution and math display
        katex_elements = self.driver.find_elements(By.CSS_SELECTOR, ".katex")
        self.assertGreater(len(katex_elements), 0)

        # Ensure no raw unparsed LaTeX like '\frac' or '\mathbb' is displayed as raw text
        body_text = self.driver.find_element(By.ID, "card-main-solution").text
        self.assertNotIn("\\frac", body_text)
        self.assertNotIn("\\mathbb", body_text)

        self._save_screenshot("13_katex_typesetting_verification")

    # -------------------------------------------------------------------------
    # Scenario 14: Verification Label Honesty Gate
    # -------------------------------------------------------------------------
    def test_14_verification_label_honesty(self):
        # 1. Native solver query -> VERIFIED_WITH_EVIDENCE
        self._submit_query("3*x + 6 = 0")
        WebDriverWait(self.driver, 5.0).until(
            lambda d: "status-valid-cert" in d.find_element(By.ID, "res-cert-badge").get_attribute("class")
        )
        badge_native = self.driver.find_element(By.ID, "res-cert-badge")
        self.assertTrue("CHỨNG THỰC TẤT ĐỊNH" in badge_native.text or "DETERMINISTIC VERIFICATION" in badge_native.text)
        self.assertEqual(badge_native.get_attribute("class"), "cert-status status-valid-cert")

        # 2. SymPy CAS query -> COMPUTED (Honest badge, not claiming MKE proof)
        self._submit_query("x^3 - 8 = 0")
        WebDriverWait(self.driver, 5.0).until(
            lambda d: "status-computed-cert" in d.find_element(By.ID, "res-cert-badge").get_attribute("class")
        )
        badge_cas = self.driver.find_element(By.ID, "res-cert-badge")
        self.assertIn("COMPUTED", badge_cas.text)
        self.assertIn("status-computed-cert", badge_cas.get_attribute("class"))

        self._save_screenshot("14_verification_honesty_check")

    # -------------------------------------------------------------------------
    # Scenario 15: Input vs Output Card Separation
    # -------------------------------------------------------------------------
    def test_15_input_vs_output_separation(self):
        self._submit_query("2*x + 3 = 7")
        self._wait_for_math_render()

        # Input card: must show the submitted expression (2*x + 3 = 7), NOT the solution
        input_display = self.driver.find_element(By.ID, "res-math-display").text
        self.assertIn("2", input_display)
        self.assertIn("x", input_display)
        self.assertIn("3", input_display)
        self.assertIn("7", input_display)
        self.assertNotIn("{2}", input_display)

        # Solution card: must show the exact solution value 2
        sol_val = self.driver.find_element(By.ID, "res-solution-val").text
        self.assertIn("2", sol_val)

        self._save_screenshot("15_input_vs_output_separation")

    # -------------------------------------------------------------------------
    # Scenario 16: HTTP 400 Invalid Input Preserves Online Connection
    # -------------------------------------------------------------------------
    def test_16_http_400_preserves_online_connection(self):
        self._submit_query("1 / 0")
        time.sleep(0.5)

        # Verify status is syntax invalid / domain error
        syntax_status = self.driver.find_element(By.ID, "res-syntax-status").text
        self.assertTrue("LỖI" in syntax_status or "KHÔNG HỢP LỆ" in syntax_status or "INVALID" in syntax_status)

        # Verify server connection banner remains CONNECTED (not CONNECTION_ERROR!)
        banner = self.driver.find_element(By.ID, "app-connection-banner")
        self.assertIn("banner-connected", banner.get_attribute("class"))

        # Verify error message displayed in solution box
        sol_val = self.driver.find_element(By.ID, "res-solution-val").text
        self.assertTrue("Division by zero" in sol_val or "0" in sol_val)

        self._save_screenshot("16_http_400_invalid_syntax")

    # -------------------------------------------------------------------------
    # Scenario 17: HTTP 403 Security Rejection Preserves Online Connection
    # -------------------------------------------------------------------------
    def test_17_http_403_preserves_online_connection(self):
        self._submit_query("__import__('os').system('dir')")
        time.sleep(0.5)

        # Verify status is security rejected
        syntax_status = self.driver.find_element(By.ID, "res-syntax-status").text
        self.assertTrue("BẢO MẬT" in syntax_status or "SECURITY" in syntax_status)

        # Verify server connection banner remains CONNECTED
        banner = self.driver.find_element(By.ID, "app-connection-banner")
        self.assertIn("banner-connected", banner.get_attribute("class"))

        self._save_screenshot("17_http_403_security_rejected")

    # -------------------------------------------------------------------------
    # Scenario 18: Immediate Disconnection Banner Update
    # -------------------------------------------------------------------------
    def test_18_immediate_disconnection_banner_update(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")

        # Simulate network drop by overriding window.fetch
        self.driver.execute_script("""
            window.fetch = function() {
                return Promise.reject(new TypeError('Failed to fetch (Network unreachable)'));
            };
        """)

        math_input = self.driver.find_element(By.ID, "math-input")
        math_input.clear()
        math_input.send_keys("x + 1 = 2")
        self.driver.find_element(By.CLASS_NAME, "compute-btn").click()

        WebDriverWait(self.driver, 5.0).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#screen-result.active"))
        )
        time.sleep(0.3)

        # Verify connection banner immediately flipped to DISCONNECTED without delay
        banner = self.driver.find_element(By.ID, "app-connection-banner")
        self.assertIn("banner-disconnected", banner.get_attribute("class"))

    # -------------------------------------------------------------------------
    # Scenario 19: Strict Verification Contract Fallback (Missing/Invalid Status)
    # -------------------------------------------------------------------------
    def test_19_strict_verification_contract_fallback(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")

        # Mock fetch while still on home screen
        self.driver.execute_script("""
            window.fetch = function() {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        mathematical_status: "SUCCESS",
                        selected_engine: "mke_native_v1",
                        symbolic_result: "x = 5",
                        canonical_steps: [{step_num: "Bước 1", description: "Biến đổi", math: "x = 5"}],
                        execution_duration_sec: 0.001
                        // verification_status is deliberately omitted!
                    })
                });
            };
        """)

        math_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.ID, "math-input"))
        )
        math_input.clear()
        math_input.send_keys("x = 5")
        self.driver.find_element(By.CLASS_NAME, "compute-btn").click()

        WebDriverWait(self.driver, 5.0).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#screen-result.active"))
        )
        time.sleep(0.5)

        # Must display CHƯA KIỂM ĐỊNH (NOT_VERIFIED), NOT VERIFIED_WITH_EVIDENCE!
        cert_badge = self.driver.find_element(By.ID, "res-cert-badge")
        self.assertIn("CHƯA KIỂM ĐỊNH", cert_badge.text)
        self.assertIn("status-unverified-cert", cert_badge.get_attribute("class"))

        self._save_screenshot("19_strict_verification_fallback")

    # -------------------------------------------------------------------------
    # Scenario 20: Explicit Domain Certainty Rendering
    # -------------------------------------------------------------------------
    def test_20_explicit_domain_certainty_rendering(self):
        # 1. Proven reals
        self._submit_query("2*x + 3 = 7")
        time.sleep(0.5)
        eq_domain = self.driver.find_element(By.ID, "res-eq-domain")
        self.assertTrue("katex" in eq_domain.get_attribute("innerHTML"))

        # 2. Explicit exclusions (rational)
        self._submit_query("simplify((x^2 - 1)/(x - 1))")
        time.sleep(0.5)
        eq_domain = self.driver.find_element(By.ID, "res-eq-domain")
        self.assertIn("1", eq_domain.text)

        self._save_screenshot("20_explicit_domain_certainty")

    # -------------------------------------------------------------------------
    # Scenario 21: Honest Presentation of Non-Success Status (No Green Badge)
    # -------------------------------------------------------------------------
    def test_21_honest_presentation_non_success_statuses(self):
        self.driver.get(f"{self.base_url}/?lang=vi&theme=light")

        # Test OUT_OF_SCOPE presentation
        self.driver.execute_script("""
            window.fetch = function() {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        mathematical_status: "OUT_OF_SCOPE",
                        verification_status: "ERROR",
                        selected_engine: "mke_native_v1",
                        error_message: "Operation out of scope for Native MKE."
                    })
                });
            };
        """)

        math_input = self.driver.find_element(By.ID, "math-input")
        math_input.clear()
        math_input.send_keys("cos(x)")
        self.driver.find_element(By.CLASS_NAME, "compute-btn").click()
        time.sleep(0.5)

        syntax_status = self.driver.find_element(By.ID, "res-syntax-status")
        # Ensure it is NOT green status-valid!
        self.assertNotIn("status-valid", syntax_status.get_attribute("class"))
        self.assertIn("status-invalid", syntax_status.get_attribute("class"))
        self.assertIn("VƯỢT QUÁ PHẠM VI", syntax_status.text)

        # Ensure cert badge is status-invalid-cert
        cert_badge = self.driver.find_element(By.ID, "res-cert-badge")
        self.assertIn("status-invalid-cert", cert_badge.get_attribute("class"))

        self._save_screenshot("21_honest_out_of_scope_presentation")


if __name__ == "__main__":
    unittest.main()

