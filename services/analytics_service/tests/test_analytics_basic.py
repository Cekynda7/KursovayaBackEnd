from fastapi.testclient import TestClient

from analytics_service.main import app


client = TestClient(app)


def test_events_endpoint_works():
    response = client.get("/events")
    # При пустой БД должны получить 200 и JSON с items
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


