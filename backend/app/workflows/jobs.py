import asyncio
import logging
from copy import deepcopy
from uuid import uuid4

from app.ingestion.urls import IntakeError
from app.storage.repository import Conflict, StorageError
from app.workflows.models import IntakeJob, IntakeRequest, ProgressEvent, ReviewRequired, WorkflowStep
from app.workflows.service import IngestionWorkflow

logger = logging.getLogger(__name__)


class IngestionJobs:
    def __init__(self):
        self.jobs: dict[str, IntakeJob] = {}
        self.tasks: set[asyncio.Task] = set()

    def create(self, request: IntakeRequest, workflow: IngestionWorkflow) -> IntakeJob:
        if len(self.jobs) >= 100:
            finished = next((key for key, value in self.jobs.items() if value.status in {"complete", "needs_review", "failed"}), None)
            if finished:
                self.jobs.pop(finished)
            else:
                raise ValueError("Too many ingestion jobs are running. Wait for one to finish.")
        job = IntakeJob(id=str(uuid4()), events=[ProgressEvent(step=WorkflowStep.QUEUED, message="Queued for local processing.")])
        self.jobs[job.id] = job
        task = asyncio.create_task(self._run(job, request, workflow))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return deepcopy(job)

    async def _progress(self, job: IntakeJob, step: WorkflowStep, message: str):
        job.step = step
        job.message = message
        job.events.append(ProgressEvent(step=step, message=message))
        await asyncio.sleep(0)

    async def _run(self, job: IntakeJob, request: IntakeRequest, workflow: IngestionWorkflow):
        job.status = "running"
        try:
            result = await workflow.run(request, lambda step, message: self._progress(job, step, message))
            job.result = result
            job.status = "complete"
            await self._progress(job, WorkflowStep.COMPLETE, "Products are ready to preview.")
        except ReviewRequired as error:
            job.status = "needs_review"
            if error.evidence:
                job.review_evidence.append(error.evidence)
            await self._progress(job, WorkflowStep.NEEDS_REVIEW, str(error))
        except (IntakeError, Conflict, StorageError) as error:
            job.status = "failed"
            message = str(error).strip() or "Product ingestion failed. Review the URLs and try again."
            await self._progress(job, WorkflowStep.FAILED, message)
        except Exception:
            logger.exception("Unexpected product ingestion failure for job %s", job.id)
            job.status = "failed"
            await self._progress(
                job,
                WorkflowStep.FAILED,
                "Product ingestion failed unexpectedly. Review the URLs, backend logs, and provider configuration.",
            )

    def get(self, job_id: str) -> IntakeJob:
        if job_id not in self.jobs:
            from app.storage.repository import NotFound
            raise NotFound("Ingestion job not found.")
        return deepcopy(self.jobs[job_id])

    async def close(self):
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
