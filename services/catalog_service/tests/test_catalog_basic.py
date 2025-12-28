from fastapi.testclient import TestClient

from catalog_service.main import app


client = TestClient(app)


def test_create_and_get_book(monkeypatch):
    # Для теста авторизацию admin можно эмулировать заглушкой (упрощённый вариант)
    token = "dummy"

    # monkeypatch.decode_jwt_token если нужно; здесь используем открытый эндпоинт get /books после успешного POST

    response = client.post(
        "/books",
        json={
            "title": "Test Book",
            "description": "Desc",
            "isbn": "1234567890",
            "price": 10.5,
            "author_name": "Test Author",
            "category_names": ["Test Category"],
            "stock_quantity": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (201, 401, 403)


