"""
MKE MVP V1 — Production Composition & Real Browser E2E Suite.

Tests genuine browser interactions on the production ASGI product app:
Browser -> Built React Frontend -> Same-Origin /api/v1/* -> FastAPI -> S1 Math Engine.
Uses Selenium with Headless Chrome. No mocked fetch.
"""

from __future__ import annotations

import os
import pathlib
import socket
import sys
import threading
import time
import unittest
import urllib.request
import uvicorn

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mke_product.product_app import app as product_asgi_app


def find_free_port() -> int:
    """Find a dynamically available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestMVPV1ReactE2E(unittest.TestCase):
    """End-to-End browser test suite for MKE MVP V1 Production React Workspace."""

    driver: webdriver.Chrome
    server: uvicorn.Server
    server_thread: threading.Thread
    base_url: str

    @classmethod
    def setUpClass(cls):
        # 1. Ensure frontend dist exists before launching production app
        dist_index = REPO_ROOT / "src" / "frontend" / "dist" / "index.html"
        if not dist_index.is_file():
            raise RuntimeError(
                f"Frontend dist not found at {dist_index}. Please run 'npm run build' in src/frontend."
            )

        # 2. Start Uvicorn production ASGI server on ephemeral port
        port = find_free_port()
        cls.base_url = f"http://127.0.0.1:{port}"

        config = uvicorn.Config(
            app=product_asgi_app,
            host="127.0.0.1",
            port=port,
            log_level="error",
        )
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()

        # 3. Poll server readiness via health endpoint
        ready = False
        health_url = f"{cls.base_url}/api/v1/health"
        for _ in range(50):
            try:
                with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.1)

        if not ready:
            cls.server.should_exit = True
            cls.server_thread.join(timeout=2.0)
            raise RuntimeError(f"Server failed to become ready at {health_url}")

        # 4. Start Selenium Headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1366,850")
        chrome_options.add_argument("--disable-dev-shm-usage")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(5.0)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver"):
            cls.driver.quit()
        if hasattr(cls, "server"):
            cls.server.should_exit = True
            cls.server_thread.join(timeout=3.0)

    def _wait_for_math_render(self, timeout: float = 5.0):
        """Wait for KaTeX elements to be present in DOM."""
        WebDriverWait(self.driver, timeout).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, "katex")) > 0
        )

    # -------------------------------------------------------------------------
    # TEST CASES
    # -------------------------------------------------------------------------

    def test_01_production_homepage_initial_state(self):
        """Section 16: Verify production homepage loads with clean initial state and offline assets."""
        self.driver.get(f"{self.base_url}/")

        # React root container
        root = WebDriverWait(self.driver, 5.0).until(
            EC.presence_of_element_located((By.ID, "root"))
        )
        assert root is not None

        # Equation input
        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        assert equation_input.is_displayed()

        # Compute button
        compute_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']")
        assert compute_btn.is_displayed()

        # Empty workspace state
        empty_state = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='workspace-empty-state']")
        assert empty_state.is_displayed()
        assert "Không gian Làm việc Đại số" in empty_state.text

        # Zero fake solution initially
        assert len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='solved-workspace']")) == 0

    def test_02_raw_quadratic_solve_and_verification(self):
        """Section 17: Submit raw quadratic equation and verify SOLVED workspace, roots, and certificate."""
        self.driver.get(f"{self.base_url}/")

        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 - 5*x + 6 = 0")

        compute_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']")
        compute_btn.click()

        # Wait for SOLVED workspace to render
        solved_ws = WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='solved-workspace']"))
        )
        assert solved_ws.is_displayed()

        # Solution outcome badge
        outcome_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='solution-outcome-badge']")
        assert "2 nghiệm thực phân biệt" in outcome_badge.text

        # Roots
        root0 = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='root-latex-0']")
        root1 = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='root-latex-1']")
        assert "2" in root0.text
        assert "3" in root1.text

        # Independent Verification Certificate
        cert_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='verification-outcome-badge']")
        assert "Xác thực Toàn diện Thành công" in cert_badge.text

        # Open collapsible technical details to inspect certificate ID and fingerprint
        tech_details = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='verification-technical-details']")
        tech_details.find_element(By.TAG_NAME, "summary").click()

        cert_id = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='certificate-id']")
        assert len(cert_id.text.strip()) > 0

        fingerprint = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='integrity-fingerprint']")
        assert len(fingerprint.text.strip()) == 64  # SHA-256 hex digest

        # Trace Panel
        trace_panel = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='trace-panel']")
        assert trace_panel.is_displayed()

    def test_03_method_catalog_renders_nine_frozen_methods(self):
        """Section 18: Verify all 9 backend registered methods are dynamically rendered in the catalog."""
        self.driver.get(f"{self.base_url}/")

        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 - 5*x + 6 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='method-catalog-panel']"))
        )

        expected_methods = [
            "QUAD_FORMULA_STANDARD",
            "QUAD_FORMULA_REDUCED",
            "QUAD_FACTORIZATION_Q",
            "QUAD_FACTORIZATION_R",
            "QUAD_COMPLETE_SQUARE",
            "QUAD_VIETE_SPECIAL_SUM",
            "QUAD_VIETE_SPECIAL_DIF",
            "QUAD_VIETE_SUM_PRODUCT",
            "QUAD_GRAPHICAL_ANALYSIS",
        ]

        for method_id in expected_methods:
            card = self.driver.find_element(By.CSS_SELECTOR, f"[data-testid='method-card-{method_id}']")
            assert card.is_displayed(), f"Method card {method_id} should be visible"

        # Check methods count badge: '9 phương thức'
        catalog_panel = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='method-catalog-panel']")
        assert "9" in catalog_panel.text

    def test_04_method_switch_unexecutable_and_executable(self):
        """Section 19: Verify UNAVAILABLE method action is disabled, and switch between AVAILABLE methods."""
        self.driver.get(f"{self.base_url}/")

        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 - 5*x + 6 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='method-card-QUAD_COMPLETE_SQUARE']"))
        )

        # 1. Verify UNAVAILABLE method QUAD_COMPLETE_SQUARE has disabled solve button and openable knowledge surface
        card_complete_sq = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='method-card-QUAD_COMPLETE_SQUARE']")
        solve_btn_complete_sq = card_complete_sq.find_element(By.CSS_SELECTOR, "[data-testid='select-method-btn-QUAD_COMPLETE_SQUARE']")
        assert not solve_btn_complete_sq.is_enabled()
        assert "Chưa hỗ trợ giải" in solve_btn_complete_sq.text

        why_btn_complete_sq = card_complete_sq.find_element(By.CSS_SELECTOR, "[data-testid='why-method-btn-QUAD_COMPLETE_SQUARE']")
        why_btn_complete_sq.click()
        surface = WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='method-knowledge-surface-QUAD_COMPLETE_SQUARE']"))
        )
        assert surface.is_displayed()

        # 2. Switch to AVAILABLE method: QUAD_FORMULA_REDUCED
        card_reduced = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='method-card-QUAD_FORMULA_REDUCED']")
        switch_btn_reduced = card_reduced.find_element(By.CSS_SELECTOR, "[data-testid='select-method-btn-QUAD_FORMULA_REDUCED']")
        assert switch_btn_reduced.is_enabled()
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", switch_btn_reduced)
        time.sleep(0.2)
        self.driver.execute_script("arguments[0].click();", switch_btn_reduced)

        # Wait for SOLVED workspace with QUAD_FORMULA_REDUCED
        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='solution-summary-panel']"))
        )
        outcome_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='solution-outcome-badge']")
        assert "2 nghiệm thực phân biệt" in outcome_badge.text

        # 3. Switch back to AVAILABLE method: QUAD_FORMULA_STANDARD
        card_std = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='method-card-QUAD_FORMULA_STANDARD']")
        std_btn = card_std.find_element(By.CSS_SELECTOR, "[data-testid='select-method-btn-QUAD_FORMULA_STANDARD']")
        assert std_btn.is_enabled()
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", std_btn)
        time.sleep(0.2)
        self.driver.execute_script("arguments[0].click();", std_btn)

        # Wait for SOLVED workspace to return
        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='solution-summary-panel']"))
        )
        outcome_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='solution-outcome-badge']")
        assert "2 nghiệm thực phân biệt" in outcome_badge.text

    def test_05_reactive_coefficient_edit_and_recomputation(self):
        """Section 20: Edit coefficient c (6 -> 7) directly in editor, wait for 350ms debounce and backend recomputation."""
        self.driver.get(f"{self.base_url}/")

        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 - 5*x + 6 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='coeff-c-num']"))
        )

        # Coefficient c numerator starts at 6
        c_num_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='coeff-c-num']")
        assert c_num_input.get_attribute("value") == "6"

        # Edit c numerator: 6 -> 7
        c_num_input.click()
        c_num_input.send_keys(Keys.BACKSPACE)
        c_num_input.send_keys("7")

        # Wait past 350ms debounce + backend recomputation for x^2 - 5x + 7 = 0 (Delta = 25 - 28 = -3 < 0 -> NO_REAL_ROOTS)
        WebDriverWait(self.driver, 8.0).until(
            lambda d: "Vô nghiệm trên" in d.find_element(By.CSS_SELECTOR, "[data-testid='solution-outcome-badge']").text
        )

        outcome_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='solution-outcome-badge']")
        assert "Vô nghiệm" in outcome_badge.text

        # Source mode badge should now indicate COEFFICIENTS
        source_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='source-mode-badge']")
        assert "Phiên bản đang chỉnh sửa theo hệ số" in source_badge.text

    def test_06_quadratic_to_degenerate_transition(self):
        """Section 21: Edit a numerator 1 -> 0 and verify seamless transition to Degenerate linear workspace."""
        self.driver.get(f"{self.base_url}/")

        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 + 2*x - 4 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='coeff-a-num']"))
        )

        # Edit a numerator: 1 -> 0
        a_num_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='coeff-a-num']")
        a_num_input.click()
        a_num_input.send_keys(Keys.CONTROL + "a")
        a_num_input.send_keys("0")

        # Wait for Degenerate workspace to render (2x - 4 = 0 -> root x = 2)
        degen_ws = WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='degenerate-workspace']"))
        )
        assert degen_ws.is_displayed()

        outcome_badge = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='degenerate-outcome-badge']")
        assert "1 nghiệm bậc nhất duy nhất" in outcome_badge.text

        linear_root = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='degenerate-linear-root']")
        assert "2" in linear_root.text

        # Quadratic method catalog should be removed
        assert len(self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='method-catalog-panel']")) == 0

    def test_07_degenerate_to_quadratic_transition(self):
        """Section 22: Edit a numerator 0 -> 1 and verify return to Quadratic workspace without page reload."""
        self.driver.get(f"{self.base_url}/")

        # Initial degenerate linear equation
        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("2*x - 4 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='degenerate-workspace']"))
        )

        # Edit a numerator: 0 -> 1
        a_num_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='coeff-a-num']")
        a_num_input.click()
        a_num_input.send_keys(Keys.CONTROL + "a")
        a_num_input.send_keys("1")

        # Wait for Quadratic solved workspace to return (x^2 + 2x - 4 = 0)
        solved_ws = WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='solved-workspace']"))
        )
        assert solved_ws.is_displayed()

        # Method catalog returns with 9 methods
        catalog = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='method-catalog-panel']")
        assert catalog.is_displayed()
        assert "9" in catalog.text

    def test_08_application_syntax_error_presentation(self):
        """Section 23: Submit invalid syntax and verify safe ApplicationErrorPanel without browser crash."""
        self.driver.get(f"{self.base_url}/")

        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 ++ 5 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        # Wait for ApplicationErrorPanel
        err_panel = WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='application-error-panel']"))
        )
        assert err_panel.is_displayed()

        err_code = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='application-error-code']")
        assert "SYNTAX_ERROR" in err_code.text

        err_msg = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='application-error-message']")
        assert "Cú pháp" in err_msg.text or "SYNTAX_ERROR" in err_code.text

    def test_09_preference_language_and_theme_switching(self):
        """Section 24: Verify bilingual (VI/EN) and theme (light/dark) switching updates DOM attributes."""
        self.driver.get(f"{self.base_url}/")

        # Open settings popover
        settings_trigger = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Cài đặt hệ thống'], button[aria-haspopup='dialog']"))
        )
        settings_trigger.click()

        time.sleep(0.3)

        # 1. Switch to English
        en_btn = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'English')]"))
        )
        en_btn.click()

        time.sleep(0.3)
        html_elem = self.driver.find_element(By.TAG_NAME, "html")
        assert html_elem.get_attribute("lang") == "en"

        # 2. Switch to Dark theme
        dark_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Dark') or contains(., 'Tối')]")
        dark_btn.click()

        time.sleep(0.3)
        assert html_elem.get_attribute("data-theme") == "dark"

        # 3. Switch back to Light theme
        light_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Light') or contains(., 'Sáng')]")
        light_btn.click()

        time.sleep(0.3)
        assert html_elem.get_attribute("data-theme") == "light"

        # 4. Switch back to Vietnamese
        vi_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Tiếng Việt')]")
        vi_btn.click()

        time.sleep(0.3)
        assert html_elem.get_attribute("lang") == "vi"

    def test_10_responsive_mobile_viewport_smoke(self):
        """Section 25: Verify responsive layout on mobile viewport (390x844) with reachable Coefficient Editor."""
        self.driver.get(f"{self.base_url}/")

        # Set mobile viewport
        self.driver.set_window_size(390, 844)
        time.sleep(0.3)

        # Equation input must remain reachable and clickable
        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        assert equation_input.is_displayed()
        equation_input.clear()
        equation_input.send_keys("x^2 - 5*x + 6 = 0")

        compute_btn = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']")
        compute_btn.click()

        # Wait for CoefficientEditorPanel to appear and verify visible inputs
        coeff_panel = WebDriverWait(self.driver, 8.0).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='coefficient-editor-panel']"))
        )
        assert coeff_panel.is_displayed()

        coeff_a = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='coeff-a-num']")
        coeff_b = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='coeff-b-num']")
        coeff_c = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='coeff-c-num']")
        assert coeff_a.is_displayed()
        assert coeff_b.is_displayed()
        assert coeff_c.is_displayed()

        # Verify no major horizontal scroll overflow: scrollWidth <= clientWidth + 10
        scroll_width = self.driver.execute_script("return document.documentElement.scrollWidth;")
        client_width = self.driver.execute_script("return document.documentElement.clientWidth;")
        assert scroll_width <= client_width + 10, f"Horizontal overflow: scrollWidth ({scroll_width}) > clientWidth ({client_width})"

        # Restore desktop viewport
        self.driver.set_window_size(1366, 850)

    def test_11_offline_katex_assets_same_origin(self):
        """Section 26: Verify KaTeX CSS, scripts, and fonts load from same origin with zero external CDN dependency."""
        self.driver.get(f"{self.base_url}/")

        # A. Collect stylesheet links whose href contains "katex" (require len >= 1)
        all_links = self.driver.find_elements(By.CSS_SELECTOR, "link[rel='stylesheet']")
        katex_stylesheets = [
            link.get_attribute("href") or ""
            for link in all_links
            if "katex" in (link.get_attribute("href") or "")
        ]
        assert len(katex_stylesheets) >= 1, "Expected at least one KaTeX stylesheet link"

        # B. Require all KaTeX stylesheet URLs are same-origin
        for href in katex_stylesheets:
            assert href.startswith(self.base_url) or href.startswith("/"), f"KaTeX CSS not same-origin: {href}"
            assert "cdnjs" not in href and "jsdelivr" not in href and "unpkg" not in href

        # C. Collect relevant KaTeX script src URLs and require local same-origin
        all_scripts = self.driver.find_elements(By.TAG_NAME, "script")
        katex_scripts = [
            s.get_attribute("src") or ""
            for s in all_scripts
            if "katex" in (s.get_attribute("src") or "")
        ]
        assert len(katex_scripts) >= 1, "Expected at least one local KaTeX script tag"
        for src in katex_scripts:
            assert src.startswith(self.base_url) or src.startswith("/"), f"KaTeX script not same-origin: {src}"
            assert "cdnjs" not in src and "jsdelivr" not in src and "unpkg" not in src

        # D. Perform a real quadratic solve and verify at least one DOM element with class .katex
        equation_input = WebDriverWait(self.driver, 5.0).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='equation-input']"))
        )
        equation_input.clear()
        equation_input.send_keys("x^2 - 5*x + 6 = 0")
        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='compute-btn']").click()

        WebDriverWait(self.driver, 8.0).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, "katex")) > 0
        )
        katex_elements = self.driver.find_elements(By.CLASS_NAME, "katex")
        assert len(katex_elements) >= 1, "Expected rendered .katex elements in solved workspace"

        # E. Verify at least one known WOFF2 KaTeX asset can be loaded from same production origin with HTTP 200
        font_url = f"{self.base_url}/vendor/katex/fonts/KaTeX_Main-Regular.woff2"
        with urllib.request.urlopen(font_url, timeout=3.0) as resp:
            assert resp.status == 200
            assert len(resp.read()) > 0

