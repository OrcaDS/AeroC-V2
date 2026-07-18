from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.repositories.city_repository import CityRepository
from app.schemas.city import CityOut

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=list[CityOut])
def get_cities(db: Session = Depends(get_db)):
    repo = CityRepository(db)
    return repo.get_active()


@router.get("/{city_id}", response_model=CityOut)
def get_city(city_id: int, db: Session = Depends(get_db)):
    repo = CityRepository(db)
    city = repo.get_by_id(city_id)

    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    return city
