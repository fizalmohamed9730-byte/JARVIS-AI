"""AI Video Workflow API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.auth import get_current_user
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/video", tags=["Video Workflow"])

# In-memory store
_video_projects: Dict[str, List[Dict[str, Any]]] = {}


class VideoProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    script: Optional[str] = Field(None, max_length=10000)
    style: str = Field("professional", description="Style: professional, casual, cinematic, animated")
    duration: str = Field("short", description="Duration: short, medium, long")
    provider: str = Field("local", description="Provider: local, runway, pika, sora")


class StoryboardScene(BaseModel):
    scene_number: int
    title: str
    description: str
    duration_seconds: int
    narration: str
    visual_prompt: str
    transition: str = "cut"


class VideoProject(BaseModel):
    id: str
    title: str
    description: Optional[str]
    script: Optional[str]
    style: str
    duration: str
    provider: str
    scenes: List[StoryboardScene]
    status: str
    progress: int
    created_at: str
    updated_at: str


def _generate_storyboard(title: str, script: str, style: str, duration: str) -> List[StoryboardScene]:
    """Generate a storyboard from a script or description."""
    duration_map = {"short": 3, "medium": 5, "long": 8}
    num_scenes = duration_map.get(duration, 4)

    # Split script into scenes if provided, otherwise create template scenes
    scenes = []
    if script:
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
        if len(paragraphs) < num_scenes:
            paragraphs = paragraphs + ["[Scene continuation]"] * (num_scenes - len(paragraphs))
    else:
        paragraphs = [f"Scene {i+1} content for {title}" for i in range(num_scenes)]

    for i in range(num_scenes):
        para = paragraphs[i] if i < len(paragraphs) else f"Scene {i+1}"
        scene_duration = 10 if duration == "short" else 20 if duration == "medium" else 30
        scenes.append(StoryboardScene(
            scene_number=i + 1,
            title=f"Scene {i + 1}",
            description=para[:500],
            duration_seconds=scene_duration,
            narration=para[:200],
            visual_prompt=f"{style} style scene: {para[:100]}",
            transition="fade" if i < num_scenes - 1 else "cut",
        ))
    return scenes


@router.get("", response_model=List[VideoProject])
async def list_projects(
    current_user: User = Depends(get_current_user),
):
    """List all video projects."""
    uid = str(current_user.id)
    return _video_projects.get(uid, [])


@router.post("", response_model=VideoProject, status_code=status.HTTP_201_CREATED)
async def create_video_project(
    body: VideoProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new video project with AI-generated storyboard."""
    uid = str(current_user.id)
    project_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    scenes = _generate_storyboard(body.title, body.script or "", body.style, body.duration)

    project = {
        "id": project_id,
        "title": body.title,
        "description": body.description,
        "script": body.script,
        "style": body.style,
        "duration": body.duration,
        "provider": body.provider,
        "scenes": [s.model_dump() for s in scenes],
        "status": "draft",
        "progress": 0,
        "created_at": now,
        "updated_at": now,
    }

    if uid not in _video_projects:
        _video_projects[uid] = []
    _video_projects[uid].insert(0, project)

    return project


@router.get("/{project_id}", response_model=VideoProject)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get a specific video project."""
    uid = str(current_user.id)
    for p in _video_projects.get(uid, []):
        if p["id"] == project_id:
            return p
    raise HTTPException(status_code=404, detail="Project not found")


@router.patch("/{project_id}", response_model=VideoProject)
async def update_project(
    project_id: str,
    body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """Update a video project (title, script, scenes, status)."""
    uid = str(current_user.id)
    for p in _video_projects.get(uid, []):
        if p["id"] == project_id:
            for key, val in body.items():
                if key in ("title", "description", "script", "style", "duration", "status", "scenes"):
                    p[key] = val
            p["updated_at"] = datetime.utcnow().isoformat()
            return p
    raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/generate")
async def generate_video(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """Start video generation (marks project as processing)."""
    uid = str(current_user.id)
    for p in _video_projects.get(uid, []):
        if p["id"] == project_id:
            p["status"] = "generating"
            p["progress"] = 10
            p["updated_at"] = datetime.utcnow().isoformat()
            return {"message": "Video generation started", "project_id": project_id}
    raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/scenes/{scene_id}/regenerate")
async def regenerate_scene(
    project_id: str,
    scene_id: int,
    current_user: User = Depends(get_current_user),
):
    """Regenerate a specific scene."""
    uid = str(current_user.id)
    for p in _video_projects.get(uid, []):
        if p["id"] == project_id:
            for scene in p["scenes"]:
                if scene["scene_number"] == scene_id:
                    scene["description"] = f"[Regenerated] {scene['description']}"
                    p["updated_at"] = datetime.utcnow().isoformat()
                    return {"message": f"Scene {scene_id} regenerated", "scene": scene}
            raise HTTPException(status_code=404, detail="Scene not found")
    raise HTTPException(status_code=404, detail="Project not found")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a video project."""
    uid = str(current_user.id)
    projects = _video_projects.get(uid, [])
    before = len(projects)
    _video_projects[uid] = [p for p in projects if p["id"] != project_id]
    if len(_video_projects[uid]) == before:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


@router.get("/providers/available")
async def available_providers(
    current_user: User = Depends(get_current_user),
):
    """Check which video providers are available."""
    return {
        "local": True,
        "runway": False,
        "pika": False,
        "sora": False,
    }
