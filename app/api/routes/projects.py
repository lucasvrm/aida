from fastapi import APIRouter, Depends
from app.api.deps import verify_internal_token
from app.models.schemas import ProjectResponse, OutputUrlResponse
from app.services.job_service import JobService

router = APIRouter(tags=["projects"], dependencies=[Depends(verify_internal_token)])

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    svc = JobService()
    return await svc.get_project(project_id)

@router.get("/projects/{project_id}/output", response_model=OutputUrlResponse)
async def get_project_output(project_id: str):
    svc = JobService()
    return await svc.get_project_output_url(project_id)
