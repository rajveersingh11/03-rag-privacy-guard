import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile, Request
from starlette.datastructures import Headers

from aegisVault.app.routers import ingest


def test_read_limited_text_file_rejects_oversize(monkeypatch):
    monkeypatch.setattr(ingest, "MAX_INGEST_BYTES", 4)
    file = UploadFile(
        filename="doc.txt",
        file=BytesIO(b"12345"),
        headers=Headers({"content-type": "text/plain"}),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(ingest._read_limited_text_file(file))

    assert exc.value.status_code == 413


def test_read_limited_text_file_rejects_bad_extension():
    file = UploadFile(
        filename="doc.exe",
        file=BytesIO(b"text"),
        headers=Headers({"content-type": "text/plain"}),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(ingest._read_limited_text_file(file))

    assert exc.value.status_code == 415


def test_verify_api_key_requires_configured_secret(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    from aegisVault.app.deps import init_api_keys
    init_api_keys()

    with pytest.raises(HTTPException) as exc:
        ingest.verify_api_key(Request(scope={"type": "http"}), "anything")

    assert exc.value.status_code == 503


def test_verify_api_key_accepts_configured_secret(monkeypatch):
    monkeypatch.setenv("API_KEY", "real-secret")
    from aegisVault.app.deps import init_api_keys
    init_api_keys()

    assert ingest.verify_api_key(Request(scope={"type": "http"}), "real-secret") == "real"
