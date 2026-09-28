"""Basic smoke test: the app imports cleanly and /health responds. Cheap,
but it catches import-time breakage (e.g. a bad dependency/driver swap).

Deliberately does NOT use `TestClient` as a context manager - that would run
the app's lifespan (app/main.py), which schedules a real RSS-feed fetch on
startup. A route-level request doesn't need the scheduler running.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
