"""Acceptance and contract tests for FastAPI Static Knowledge Transport API (Stage S3-03).

Verifies:
1. HTTP 200 success matrix across all accepted knowledge entities (9 methods, 14 concepts, 5 formulas, 1 theorem, graph).
2. Exact payload equivalence with underlying KnowledgeRepository and KnowledgeGraphService models.
3. Graph export endpoint parity (29 nodes, 84 edges, KNOWLEDGE_GRAPH kind).
4. Semantic distinction between known-route/unknown-entity (404 KnowledgeApiErrorResponse) and unknown-route (404 TransportErrorResponse).
5. Read-only API guarantee (zero POST/PUT/PATCH/DELETE endpoints under /api/v1/knowledge).
6. OpenAPI contract adherence (stable operation IDs, schema refs, extra=forbid schemas).
7. Determinism across repeated requests and sanitized HTTP 500 on unexpected internal errors.
"""

from __future__ import annotations

import json
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from mke_product.knowledge.graph_models import GraphKind, GraphModel
from mke_product.knowledge.graph_service import KnowledgeGraphService
from mke_product.knowledge.repository import KnowledgeRepository
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    FormulaKnowledge,
    MethodKnowledge,
    TheoremKnowledge,
)
from mke_product.transport.app import create_app
from mke_product.transport.models import (
    KnowledgeApiErrorCode,
    KnowledgeApiErrorResponse,
    TransportErrorCode,
    TransportErrorResponse,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def repo() -> KnowledgeRepository:
    return KnowledgeRepository()


@pytest.fixture(scope="module")
def graph_service() -> KnowledgeGraphService:
    return KnowledgeGraphService()


# ============================================================================
# 1. HTTP 200 SUCCESS MATRIX (ALL ACCEPTED ENTITIES & GRAPH)
# ============================================================================

def test_http_get_all_methods_success(client: TestClient, repo: KnowledgeRepository) -> None:
    methods = repo.list_methods()
    assert len(methods) == 9

    for m in methods:
        resp = client.get(f"/api/v1/knowledge/methods/{m.method_id}")
        assert resp.status_code == 200
        data = resp.json()

        # Strict validation through Pydantic model
        validated_model = MethodKnowledge.model_validate_json(resp.text)
        assert validated_model.method_id == m.method_id

        # Exact JSON equality with repo
        assert data == m.model_dump(mode="json")


def test_http_get_all_concepts_success(client: TestClient, repo: KnowledgeRepository) -> None:
    concepts = repo.list_concepts()
    assert len(concepts) == 14

    for c in concepts:
        resp = client.get(f"/api/v1/knowledge/concepts/{c.concept_id}")
        assert resp.status_code == 200
        data = resp.json()

        # Strict validation through Pydantic model
        validated_model = ConceptKnowledge.model_validate_json(resp.text)
        assert validated_model.concept_id == c.concept_id

        # Exact JSON equality with repo
        assert data == c.model_dump(mode="json")


def test_http_get_all_formulas_success(client: TestClient, repo: KnowledgeRepository) -> None:
    formulas = repo.list_formulas()
    assert len(formulas) == 5

    for f in formulas:
        resp = client.get(f"/api/v1/knowledge/formulas/{f.formula_id}")
        assert resp.status_code == 200
        data = resp.json()

        # Strict validation through Pydantic model
        validated_model = FormulaKnowledge.model_validate_json(resp.text)
        assert validated_model.formula_id == f.formula_id

        # Exact JSON equality with repo
        assert data == f.model_dump(mode="json")


def test_http_get_all_theorems_success(client: TestClient, repo: KnowledgeRepository) -> None:
    theorems = repo.list_theorems()
    assert len(theorems) == 1

    for t in theorems:
        resp = client.get(f"/api/v1/knowledge/theorems/{t.theorem_id}")
        assert resp.status_code == 200
        data = resp.json()

        # Strict validation through Pydantic model
        validated_model = TheoremKnowledge.model_validate_json(resp.text)
        assert validated_model.theorem_id == t.theorem_id

        # Exact JSON equality with repo
        assert data == t.model_dump(mode="json")


def test_http_get_knowledge_graph_success(client: TestClient, graph_service: KnowledgeGraphService) -> None:
    resp = client.get("/api/v1/knowledge/graph")
    assert resp.status_code == 200
    data = resp.json()

    # Validate GraphModel
    graph_model = GraphModel.model_validate_json(resp.text)
    assert graph_model.graph_kind == GraphKind.KNOWLEDGE_GRAPH
    assert len(graph_model.nodes) == 29
    assert len(graph_model.edges) == 84

    # Exact equality with service export
    expected_data = graph_service.export_knowledge_graph().model_dump(mode="json")
    assert data == expected_data


# ============================================================================
# 2. DETERMINISM ACROSS REPEATED CALLS
# ============================================================================

def test_endpoints_determinism(client: TestClient) -> None:
    # Method
    r1 = client.get("/api/v1/knowledge/methods/QUAD_FORMULA_STANDARD")
    r2 = client.get("/api/v1/knowledge/methods/QUAD_FORMULA_STANDARD")
    assert r1.json() == r2.json()

    # Concept
    r1 = client.get("/api/v1/knowledge/concepts/concept_discriminant")
    r2 = client.get("/api/v1/knowledge/concepts/concept_discriminant")
    assert r1.json() == r2.json()

    # Formula
    r1 = client.get("/api/v1/knowledge/formulas/FORMULA_DISCRIMINANT")
    r2 = client.get("/api/v1/knowledge/formulas/FORMULA_DISCRIMINANT")
    assert r1.json() == r2.json()

    # Theorem
    r1 = client.get("/api/v1/knowledge/theorems/THEOREM_VIETA_RELATIONS")
    r2 = client.get("/api/v1/knowledge/theorems/THEOREM_VIETA_RELATIONS")
    assert r1.json() == r2.json()

    # Graph
    g1 = client.get("/api/v1/knowledge/graph")
    g2 = client.get("/api/v1/knowledge/graph")
    assert g1.json() == g2.json()
    assert json.dumps(g1.json(), sort_keys=True) == json.dumps(g2.json(), sort_keys=True)


# ============================================================================
# 3. ENTITY NOT FOUND MATRIX (KNOWN ROUTE + UNKNOWN ID)
# ============================================================================

@pytest.mark.parametrize(
    "path, expected_type, test_id",
    [
        ("/api/v1/knowledge/methods/UNKNOWN_METHOD", "MethodKnowledge", "UNKNOWN_METHOD"),
        ("/api/v1/knowledge/concepts/concept_nonexistent", "ConceptKnowledge", "concept_nonexistent"),
        ("/api/v1/knowledge/formulas/FORMULA_UNKNOWN", "FormulaKnowledge", "FORMULA_UNKNOWN"),
        ("/api/v1/knowledge/theorems/THEOREM_UNKNOWN", "TheoremKnowledge", "THEOREM_UNKNOWN"),
    ],
)
def test_unknown_entity_returns_knowledge_api_error_response(
    client: TestClient, path: str, expected_type: str, test_id: str
) -> None:
    resp = client.get(path)
    assert resp.status_code == 404
    data = resp.json()

    # Must parse cleanly into KnowledgeApiErrorResponse
    err = KnowledgeApiErrorResponse.model_validate_json(resp.text)
    assert err.status == "error"
    assert err.error_code == KnowledgeApiErrorCode.KNOWLEDGE_ENTITY_NOT_FOUND
    assert err.entity_type == expected_type
    assert err.entity_id == test_id
    assert test_id in err.message_vi
    assert test_id in err.message_en

    # Zero traceback / internal leakage
    assert "traceback" not in data
    assert "Traceback" not in resp.text


# ============================================================================
# 4. UNKNOWN ROUTE VS UNKNOWN ENTITY DISTINCTION
# ============================================================================

def test_unknown_route_returns_transport_api_not_found(client: TestClient) -> None:
    # 1. Completely unknown route under /api/v1/knowledge
    resp = client.get("/api/v1/knowledge/not-a-real-endpoint/whatever")
    assert resp.status_code == 404
    data = resp.json()

    # Must be TransportErrorResponse (API_NOT_FOUND), NOT KnowledgeApiErrorResponse
    err = TransportErrorResponse.model_validate_json(resp.text)
    assert err.transport_status == "ERROR"
    assert err.transport_error_code == TransportErrorCode.API_NOT_FOUND
    assert "details" in data
    assert data["details"]["path"] == "/api/v1/knowledge/not-a-real-endpoint/whatever"

    # 2. Contrast with known route + unknown entity
    entity_resp = client.get("/api/v1/knowledge/methods/NONEXISTENT")
    assert entity_resp.status_code == 404
    knowledge_err = KnowledgeApiErrorResponse.model_validate_json(entity_resp.text)
    assert knowledge_err.error_code == KnowledgeApiErrorCode.KNOWLEDGE_ENTITY_NOT_FOUND


# ============================================================================
# 5. READ-ONLY API GUARANTEE
# ============================================================================

def test_knowledge_api_is_strictly_read_only(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    knowledge_paths = {p: methods for p, methods in openapi["paths"].items() if p.startswith("/api/v1/knowledge")}

    assert len(knowledge_paths) == 5

    for path, methods_dict in knowledge_paths.items():
        assert set(methods_dict.keys()) == {"get"}, f"Non-GET method found on {path}: {methods_dict.keys()}"

    # Verify write methods return 405 Method Not Allowed via client
    for method_verb in ["post", "put", "patch", "delete"]:
        caller = getattr(client, method_verb)
        resp = caller("/api/v1/knowledge/graph")
        assert resp.status_code == 405


# ============================================================================
# 6. OPENAPI CONTRACT & OPERATION IDS
# ============================================================================

def test_openapi_knowledge_schema_contract(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    expected_ops = {
        "/api/v1/knowledge/methods/{method_id}": "get_knowledge_method_v1",
        "/api/v1/knowledge/concepts/{concept_id}": "get_knowledge_concept_v1",
        "/api/v1/knowledge/formulas/{formula_id}": "get_knowledge_formula_v1",
        "/api/v1/knowledge/theorems/{theorem_id}": "get_knowledge_theorem_v1",
        "/api/v1/knowledge/graph": "get_knowledge_graph_v1",
    }

    for path, op_id in expected_ops.items():
        assert path in paths, f"Missing path: {path}"
        get_op = paths[path]["get"]
        assert get_op["operationId"] == op_id, f"Operation ID mismatch on {path}: {get_op['operationId']}"

        # Check response documentation
        responses = get_op["responses"]
        assert "200" in responses
        assert "500" in responses
        if "{method_id}" in path or "{concept_id}" in path or "{formula_id}" in path or "{theorem_id}" in path:
            assert "404" in responses


# ============================================================================
# 7. INTERNAL FAILURE SANITIZATION (HTTP 500)
# ============================================================================

def test_internal_service_failure_is_sanitized_500(client: TestClient) -> None:
    with patch.object(KnowledgeRepository, "get_method", side_effect=RuntimeError("Secret database error /path/to/secret")):
        resp = client.get("/api/v1/knowledge/methods/QUAD_FORMULA_STANDARD")
        assert resp.status_code == 500
        data = resp.json()

        err = TransportErrorResponse.model_validate_json(resp.text)
        assert err.transport_status == "ERROR"
        assert err.transport_error_code == TransportErrorCode.INTERNAL_TRANSPORT_ERROR

        # Strict sanitization: no internal text leak
        assert "Secret" not in resp.text
        assert "secret" not in resp.text
        assert "RuntimeError" not in resp.text
