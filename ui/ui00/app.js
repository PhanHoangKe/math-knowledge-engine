/**
 * MKE PRODUCT-UI-00 — Client-Side Prototype Logic
 * Strictly self-contained: Zero external network requests, zero CDNs, local storage persistence.
 */

(function () {
  'use strict';

  // --- Theme Management ---
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
    const themeParam = urlParams.get("theme");
    const saved = themeParam || localStorage.getItem(THEME_STORAGE_KEY) || "auto";
    applyTheme(saved);

    // Listen for system theme changes when set to auto
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        const currentPref = localStorage.getItem(THEME_STORAGE_KEY) || "auto";
        if (currentPref === "auto") {
          applyTheme("auto");
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

  // --- Screen Navigation ---
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

  // --- Input and Quick Math Toolbar ---
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

  // --- Mock Result Calculation Engine (Client-Side Illustrative Demo Only) ---
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
    },
    '-x^2 = 1': {
      mathDisplay: '-x^2 = 1  [Parsed as -(x^2) = 1]',
      ast: `Equation(
  left=UnaryOp("-",
    operand=Power(base=Variable("x"), exponent=IntegerLiteral(2))),
  right=IntegerLiteral(1)
)`,
      solutionVar: 'Status',
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
    },
    'x^0 = 1': {
      mathDisplay: 'x^0 = 1',
      ast: `Equation(
  left=Power(base=Variable("x"), exponent=IntegerLiteral(0)),
  right=IntegerLiteral(1)
)`,
      solutionVar: 'Domain',
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
    },
    '0*x = 0': {
      mathDisplay: '0*x = 0',
      ast: `Equation(
  left=BinaryOp("*", left=IntegerLiteral(0), right=Variable("x")),
  right=IntegerLiteral(0)
)`,
      solutionVar: 'DomainSet',
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
  };

  function displayResult(query) {
    const trimmed = query.trim();
    const resultQueryText = document.getElementById('result-query-text');
    const mathDisplay = document.getElementById('res-math-display');
    const astJson = document.getElementById('res-ast-json');
    const solutionVal = document.getElementById('res-solution-val');
    const domainConstraints = document.getElementById('res-domain-constraints');
    const stepsList = document.getElementById('res-steps-list');

    if (resultQueryText) resultQueryText.textContent = trimmed;

    // Check if input is an implicit multiplication error demonstration
    if (trimmed.includes('2x') || trimmed.includes('1/2x') || trimmed.includes('x(')) {
      if (mathDisplay) mathDisplay.textContent = trimmed;
      if (astJson) {
        astJson.textContent = `[SYNTAX ERROR: ImplicitMultiplicationError]
Ambiguous implicit multiplication is rejected; use explicit '*' (e.g. '2*x' instead of '2x').
Source Span: position of adjacent tokens.`;
      }
      if (solutionVal) solutionVal.textContent = 'Syntax Error (Rejected)';
      if (domainConstraints) domainConstraints.textContent = 'Parsing halted before solver';
      if (stepsList) {
        stepsList.innerHTML = `
          <li class="step-item" style="border-left-color: #ef4444;">
            <div class="step-num" style="color: #ef4444;">Syntax Error</div>
            <div class="step-desc">MKE requires explicit multiplication to prevent mathematical ambiguity:</div>
            <div class="step-math">Please write <code>2*x</code> or <code>(1/2)*x</code> explicitly.</div>
          </li>
        `;
      }
      switchScreen('result');
      return;
    }

    const fixture = MOCK_FIXTURES[trimmed] || {
      mathDisplay: trimmed,
      ast: `Equation(
  left=ParsedExpression("${trimmed.split('=')[0] || ''}"),
  right=ParsedExpression("${trimmed.split('=')[1] || ''}")
)`,
      solutionVar: 'x',
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
    };

    if (mathDisplay) mathDisplay.textContent = fixture.mathDisplay;
    if (astJson) astJson.textContent = fixture.ast;
    if (solutionVal) solutionVal.textContent = fixture.solutionVal;
    if (domainConstraints) domainConstraints.textContent = fixture.domainConstraints;

    if (stepsList) {
      stepsList.innerHTML = fixture.steps.map(s => `
        <li class="step-item">
          <div class="step-num">${s.num}</div>
          <div class="step-desc">${s.desc}</div>
          <div class="step-math">${s.math}</div>
        </li>
      `).join('');
    }

    switchScreen('result');
  }

  // --- Event Listeners Setup ---
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
