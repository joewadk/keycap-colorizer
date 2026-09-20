from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.models.configuration import Configuration
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet
from app.storage.models import ConfigurationCreate, ProductRecord, RestoredConfiguration
from app.storage.repository import Repository, NotFound, product_record

router = APIRouter(tags=["local storage"])


def get_repository(settings: Settings = Depends(get_settings)) -> Repository:
    path = Path(settings.database_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path
    return Repository(path)


Repo = Annotated[Repository, Depends(get_repository)]


@router.post("/products/manual", response_model=ProductRecord, status_code=201)
def import_product(request: ProductRecord, repository: Repo):
    return product_record(repository.save_product(request.product))


@router.get("/products/{product_id}", response_model=ProductRecord)
def get_product(product_id: str, repository: Repo):
    return product_record(repository.get_product(product_id))


@router.get("/keyboards/{product_id}", response_model=KeyboardDefinition)
def get_keyboard(product_id: str, repository: Repo):
    product = repository.get_product(product_id)
    if not isinstance(product, KeyboardDefinition):
        raise NotFound("Keyboard not found.")
    return product


@router.get("/keycaps/{product_id}", response_model=KeycapSet)
def get_keycaps(product_id: str, repository: Repo):
    product = repository.get_product(product_id)
    if not isinstance(product, KeycapSet):
        raise NotFound("Keycap set not found.")
    return product


@router.post("/configurations", response_model=RestoredConfiguration, status_code=201)
def save_configuration(request: ConfigurationCreate, repository: Repo):
    return repository.save_configuration(request)


@router.get("/configurations", response_model=list[Configuration])
def list_configurations(repository: Repo, limit: Annotated[int, Query(ge=1, le=100)] = 50,
                        offset: Annotated[int, Query(ge=0)] = 0):
    return repository.list_configurations(limit=limit, offset=offset)


@router.get("/configurations/{configuration_id}", response_model=RestoredConfiguration)
def restore_configuration(configuration_id: str, repository: Repo):
    return repository.get_configuration(configuration_id)
