from fastapi import APIRouter, Depends, status
from app.api.deps import verify_internal_token
from app.models.schemas import ProjectResponse, OutputUrlResponse, CreateJobResponse
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


@router.post(
    "/projects/{project_id}/reprocess",
    response_model=CreateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_project(project_id: str):
    svc = JobService()
    job = await svc.reprocess_project(project_id)
    await svc.kickoff_job(job.job_id)
    return job
