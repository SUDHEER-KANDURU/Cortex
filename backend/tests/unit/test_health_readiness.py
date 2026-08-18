from fastapi.testclient import TestClient

from cortex.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_readiness_counts_match_registered_routes():
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200

    payload = response.json()
    api_routes = [
        route.path for route in app.routes if hasattr(route, "path") and route.path.startswith("/api/v1")
    ]

    expected = {
        "health": sum(1 for path in api_routes if path.startswith("/api/v1/health")),
        "jobs": sum(1 for path in api_routes if path.startswith("/api/v1/jobs")),
        "artifacts": sum(1 for path in api_routes if path.startswith("/api/v1/artifacts")),
        "graph": sum(1 for path in api_routes if path.startswith("/api/v1/graph")),
        "total": len(api_routes),
    }

    assert payload["endpoints"] == expected
