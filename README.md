# Math Knowledge Engine (MKE) — Product Workspace

**Package:** `mke_product`  
**Milestone:** PRODUCT-02A-S1 (Exact Mathematical Parser & Immutable AST)  
**Governance:** External Sibling Product Workspace (`../mke-product`)  
**Design Baseline Commit:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  

---

## 1. Overview

This repository represents the isolated, standalone product implementation of the Math Knowledge Engine. It is completely decoupled from the frozen research baseline and legacy G4 assets.

## 2. Directory Layout

```
mke-product/
├── .gitignore
├── README.md
├── S0_IMPLEMENTATION_REPORT.md
├── S1_IMPLEMENTATION_REPORT.md
├── src/
│   └── mke_product/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── errors.py
│       │   └── rational.py
│       └── parser/
│           ├── __init__.py
│           ├── ast.py
│           ├── errors.py
│           ├── lexer.py
│           ├── parser.py
│           └── tokens.py
└── tests/
    ├── __init__.py
    ├── test_parser.py
    └── test_rational.py
```

## 3. Running Tests

Tests use the standard Python `unittest` framework:

```bash
# Run all unit tests (S0 + S1)
python -m unittest discover -s tests -p "test_*.py" -v
```
