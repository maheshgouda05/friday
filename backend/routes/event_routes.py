from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.event import EventCreate, EventRead, EventUpdate
from backend.services import event_service


router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
):
    return event_service.create_event(db, event_data)


@router.get("/", response_model=list[EventRead])
def get_events(db: Session = Depends(get_db)):
    return event_service.get_events(db)


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = event_service.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
):
    event = event_service.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_service.update_event(db, event, event_data)


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    confirm: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    event = event_service.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Explicit confirmation is required to delete an event",
        )

    event_service.delete_event(db, event)
    return {"message": "Event deleted successfully", "event_id": event_id}