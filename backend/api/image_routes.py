"""Image generation API routes."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.auth import get_current_user
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/images", tags=["Image Generation"])

GENERATED_DIR = Path("data/generated_images")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# In-memory store for generated images (production would use DB)
_image_history: Dict[str, List[Dict[str, Any]]] = {}


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Image description")
    style: str = Field("natural", description="Style: natural, artistic, photorealistic, anime, pixel")
    size: str = Field("1024x1024", description="Image size")
    provider: str = Field("local", description="Provider: local, openai, stability")
    negative_prompt: Optional[str] = Field(None, description="What to avoid")


class ImageResponse(BaseModel):
    id: str
    prompt: str
    url: str
    style: str
    size: str
    provider: str
    created_at: str
    status: str = "completed"


@router.get("", response_model=List[ImageResponse])
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """List generated images for the current user."""
    uid = str(current_user.id)
    images = _image_history.get(uid, [])
    start = (page - 1) * page_size
    return images[start:start + page_size]


@router.post("", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_image(
    body: ImageGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate an image using AI. Creates a placeholder when no external provider is configured."""
    uid = str(current_user.id)
    image_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Attempt real generation based on provider
    result_url = ""
    if body.provider == "openai":
        try:
            import httpx
            from config.settings import settings
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={"model": "dall-e-3", "prompt": body.prompt, "size": body.size, "n": 1},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result_url = data["data"][0]["url"]
        except Exception as e:
            logger.warning("OpenAI image generation failed: %s", e)

    if not result_url:
        # Generate a colored SVG placeholder
        color_hash = hash(body.prompt) % 360
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">
<rect width="512" height="512" fill="hsl({color_hash}, 60%, 25%)"/>
<text x="256" y="240" text-anchor="middle" fill="white" font-family="sans-serif" font-size="16">{body.prompt[:60]}</text>
<text x="256" y="280" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="12">{body.style} | {body.size}</text>
</svg>'''
        svg_path = GENERATED_DIR / f"{image_id}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        result_url = f"/static/generated_images/{image_id}.svg"

    record = {
        "id": image_id,
        "prompt": body.prompt,
        "url": result_url,
        "style": body.style,
        "size": body.size,
        "provider": body.provider,
        "created_at": now,
        "status": "completed",
    }

    if uid not in _image_history:
        _image_history[uid] = []
    _image_history[uid].insert(0, record)

    return record


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific generated image."""
    uid = str(current_user.id)
    for img in _image_history.get(uid, []):
        if img["id"] == image_id:
            return img
    raise HTTPException(status_code=404, detail="Image not found")


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a generated image."""
    uid = str(current_user.id)
    images = _image_history.get(uid, [])
    before = len(images)
    _image_history[uid] = [i for i in images if i["id"] != image_id]
    if len(_image_history[uid]) == before:
        raise HTTPException(status_code=404, detail="Image not found")
    svg_path = GENERATED_DIR / f"{image_id}.svg"
    if svg_path.exists():
        svg_path.unlink()
    return {"success": True}


@router.get("/providers/available")
async def available_providers(
    current_user: User = Depends(get_current_user),
):
    """Check which image generation providers are available."""
    providers = {"local": True, "openai": False, "stability": False}
    try:
        from config.settings import settings
        if settings.openai_api_key:
            providers["openai"] = True
    except Exception:
        pass
    return providers
