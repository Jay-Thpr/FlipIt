from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn


class CleanPhotoRequest(BaseModel):
    image: str
    mime_type: str = "image/jpeg"


def get_output_dir() -> Path:
    configured = os.getenv("MOCK_NANO_BANANA_OUTPUT_DIR", ".tmp/mock_nano_banana")
    path = Path(configured).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_expected_api_key() -> str:
    return os.getenv("MOCK_NANO_BANANA_API_KEY", "").strip()


def get_public_base_url() -> str:
    return os.getenv("MOCK_NANO_BANANA_PUBLIC_BASE_URL", "http://127.0.0.1:8010").rstrip("/")


def guess_extension(mime_type: str) -> str:
    if mime_type == "image/png":
        return ".png"
    if mime_type == "image/webp":
        return ".webp"
    return ".jpg"


def write_image_copy(image_b64: str, mime_type: str) -> Path:
    image_bytes = base64.b64decode(image_b64, validate=True)
    output_path = get_output_dir() / f"clean_{uuid4().hex}{guess_extension(mime_type)}"
    output_path.write_bytes(image_bytes)
    return output_path


app = FastAPI(title="Mock Nano Banana", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/clean")
async def clean_photo(
    request: CleanPhotoRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    expected_api_key = get_expected_api_key()
    if expected_api_key:
        expected_header = f"Bearer {expected_api_key}"
        if authorization != expected_header:
            raise HTTPException(status_code=401, detail="Invalid bearer token")

    try:
        output_path = write_image_copy(request.image, request.mime_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {exc}") from exc

    return {
        "clean_photo_url": str(output_path),
        "preview_url": f"{get_public_base_url()}/files/{output_path.name}",
        "mime_type": request.mime_type,
        "mode": "mock_passthrough",
    }


@app.get("/files/{filename}")
async def get_file(filename: str) -> FileResponse:
    path = get_output_dir() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


if __name__ == "__main__":
    uvicorn.run(
        "scripts.mock_nano_banana:app",
        host=os.getenv("MOCK_NANO_BANANA_HOST", "127.0.0.1"),
        port=int(os.getenv("MOCK_NANO_BANANA_PORT", "8010")),
        reload=False,
    )
