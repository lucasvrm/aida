from fastapi import APIRouter, Depends, status
from app.api.deps import verify_internal_token
from app.models.schemas import CreateJobRequest, CreateJobResponse, JobStatusResponse
from app.services.job_service import JobService

router = APIRouter(tags=["jobs"])

@router.post(
    "/jobs",
    response_model=CreateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_internal_token)],
)
async def create_job(payload: CreateJobRequest):
    svc = JobService()
    job = await svc.create_job(payload)
    await svc.kickoff_job(job.job_id)
    return job

@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    dependencies=[Depends(verify_internal_token)],
)
async def get_job(job_id: str):
    svc = JobService()
    return await svc.get_job_status(job_id)
