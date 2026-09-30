from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.storage import Repo
from app.config import Settings, get_settings
from app.ingestion.images import ImageCache
from app.ingestion.service import ScrapingService
from app.ingestion.urls import IntakeError, normalize_url
from app.workflows.jobs import IngestionJobs
from app.workflows.models import IntakeJob, IntakeRequest
from app.workflows.service import FIXTURE_KEYBOARD_URL, FIXTURE_KEYCAP_URL, IngestionWorkflow

router = APIRouter(tags=["product ingestion"])


def _root_path(value: str, settings_file: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else settings_file / path


def get_jobs(request: Request) -> IngestionJobs:
    return request.app.state.ingestion_jobs


Jobs = Annotated[IngestionJobs, Depends(get_jobs)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/ingestion/fixtures")
def fixtures():
    return {
        "keyboardUrl": FIXTURE_KEYBOARD_URL,
        "keycapUrl": FIXTURE_KEYCAP_URL,
        "message": "Offline ANSI 75% and Botanical product fixtures; no network or API credits are used.",
    }


@router.post("/products/ingest", response_model=IntakeJob, status_code=status.HTTP_202_ACCEPTED)
async def ingest(request: IntakeRequest, repository: Repo, jobs: Jobs, settings: SettingsDep):
    # Reject malformed/private literal URLs before allocating a job. DNS checks happen in live loaders.
    keyboard_url = normalize_url(request.keyboard_url)
    keycap_url = normalize_url(request.keycap_url)
    if keyboard_url == keycap_url:
        raise IntakeError("Use two different product pages: a keyboard in the first field and a keycap set in the second.")
    provider = request.provider or settings.scraper_provider
    root = Path(__file__).resolve().parents[3]
    data_dir = _root_path(settings.data_dir, root)
    scraper = ScrapingService(data_dir, provider=provider, api_key=settings.firecrawl_api_key)
    workflow = IngestionWorkflow(repository, scraper, data_dir, ImageCache(data_dir / "images"))
    return jobs.create(request, workflow)


@router.get("/products/ingest/{job_id}", response_model=IntakeJob)
def ingestion_status(job_id: str, jobs: Jobs):
    return jobs.get(job_id)
