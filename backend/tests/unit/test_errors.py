"""Phase 1: every error leaves through the {"error": {...}} envelope."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, register_error_handlers


def _app() -> FastAPI:
    application = FastAPI()
    register_error_handlers(application)

    @application.get("/boom")
    def boom():
        raise AppError("SPOF_NOT_FOUND", "No such factory", status_code=404, details={"factory_id": "fac_x"})

    @application.get("/bad")
    def bad(q: int):
        return q

    @application.get("/crash")
    def crash():
        raise RuntimeError("unexpected")

    return application


def test_app_error_shape():
    client = TestClient(_app(), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "SPOF_NOT_FOUND"
    assert error["message"] == "No such factory"
    assert error["details"] == {"factory_id": "fac_x"}


def test_validation_error_uses_envelope_with_code_422():
    client = TestClient(_app(), raise_server_exceptions=False)
    response = client.get("/bad", params={"q": "not-an-int"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["errors"], "validation details must list the offending fields"


def test_unhandled_exception_is_500_with_envelope():
    client = TestClient(_app(), raise_server_exceptions=False)
    response = client.get("/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    # The traceback itself must not leak to the client.
    assert "unexpected" not in response.text