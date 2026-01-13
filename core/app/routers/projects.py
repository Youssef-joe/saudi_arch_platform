from __future__ import annotations

from fastapi import APIRouter
from typing import List, Dict, Any
import json
import os

router = APIRouter(prefix="/v1/projects", tags=["projects"])

# Simple in-memory storage for MVP
PROJECTS_FILE = "/tmp/sima_projects.json"

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_projects(projects):
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects, f, indent=2)

@router.get("")
def list_projects():
    """List all projects"""
    projects = load_projects()
    return {
        "data": projects,
        "count": len(projects),
        "metadata": {"timestamp": "2024-01-12"}
    }

@router.post("")
def create_project(name: str, type: str = "residential", description: str = ""):
    """Create a new project"""
    projects = load_projects()
    
    project_id = f"proj_{len(projects) + 1}"
    new_project = {
        "id": project_id,
        "name": name,
        "type": type,
        "description": description,
        "status": "active",
        "created_at": "2024-01-12T00:00:00Z"
    }
    
    projects.append(new_project)
    save_projects(projects)
    
    return {
        "data": new_project,
        "metadata": {"created": True}
    }

@router.get("/{project_id}")
def get_project(project_id: str):
    """Get a specific project"""
    projects = load_projects()
    for p in projects:
        if p.get("id") == project_id:
            return {"data": p}
    
    return {"error": f"Project {project_id} not found"}, 404
