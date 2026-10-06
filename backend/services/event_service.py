from sqlalchemy.orm import Session

from backend.models.event import Event
from backend.schemas.event import EventCreate, EventUpdate


def create_event(db: Session, event_data: EventCreate) -> Event:
    event = Event(**event_data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_events(db: Session) -> list[Event]:
    return db.query(Event).order_by(Event.date, Event.time, Event.id).all()


def get_event(db: Session, event_id: int) -> Event | None:
    return db.query(Event).filter(Event.id == event_id).first()


def update_event(db: Session, event: Event, event_data: EventUpdate) -> Event:
    for field, value in event_data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: Event) -> None:
    db.delete(event)
    db.commit()