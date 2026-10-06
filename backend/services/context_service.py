import json
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from backend.models.event import Event
from backend.models.task import Task
from backend.models.user_profile import UserProfile
from backend.utils.time import utc_now


DEFAULT_TIMEZONE = "Asia/Kolkata"
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _get_timezone(db: Session) -> ZoneInfo:
    profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
    timezone_name = profile.timezone if profile else DEFAULT_TIMEZONE
    try:
        return ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def _date_window(message: str, today: date) -> tuple[date, date, str] | None:
    text = message.lower()
    if "tomorrow" in text or "tonight" in text:
        target = today + timedelta(days=1) if "tomorrow" in text else today
        return target, target, "tomorrow" if "tomorrow" in text else "today"
    if "yesterday" in text:
        target = today - timedelta(days=1)
        return target, target, "yesterday"
    if "today" in text or "this morning" in text or "this evening" in text:
        return today, today, "today"
    if "next week" in text:
        start = today + timedelta(days=(7 - today.weekday()))
        return start, start + timedelta(days=6), "next week"
    if "this week" in text or "coming week" in text:
        return today, today + timedelta(days=6 - today.weekday()), "this week"

    weekday = next((name for name in _WEEKDAYS if re.search(rf"\b{ name }\b", text)), None)
    if weekday:
        days_ahead = (_WEEKDAYS[weekday] - today.weekday()) % 7
        if "next " + weekday in text:
            days_ahead = days_ahead or 7
        target = today + timedelta(days=days_ahead)
        return target, target, weekday.capitalize()
    return None


def _matching_events(db: Session, start: date, end: date) -> list[Event]:
    return (
        db.query(Event)
        .filter(
            Event.status == "upcoming",
            Event.date >= start,
            Event.date <= end,
        )
        .order_by(Event.date, Event.time, Event.id)
        .limit(25)
        .all()
    )


def _format_event_time(event_time: time | None) -> str:
    if event_time is None:
        return "time not set"
    return event_time.strftime("%I:%M %p").lstrip("0")


def answer_known_schedule_question(db: Session, message: str) -> str | None:
    text = message.lower()
    asks_about_schedule = bool(
        re.search(r"\b(what|which|show|list|when)\b", text)
        and re.search(r"\b(event|events|schedule|exam|meeting|appointment|have)\b", text)
    )
    if not asks_about_schedule:
        return None

    timezone_info = _get_timezone(db)
    today = utc_now().astimezone(timezone_info).date()
    window = _date_window(text, today)
    if window is None:
        return None
    start, end, label = window
    events = _matching_events(db, start, end)
    if not events:
        return f"You don't have any events saved for {label}."

    summaries = []
    for event in events:
        summary = f"{event.title} at {_format_event_time(event.time)}"
        if event.location:
            summary += f" at {event.location}"
        summaries.append(summary)
    if len(summaries) == 1:
        return f"You have {summaries[0]} {label}."
    joined = ", and ".join([", ".join(summaries[:-1]), summaries[-1]])
    return f"You have {len(summaries)} events {label}: {joined}."


def build_relevant_context(db: Session, message: str) -> str:
    timezone_info = _get_timezone(db)
    local_now = utc_now().astimezone(timezone_info)
    text = message.lower()
    context: dict[str, object] = {
        "local_datetime": local_now.isoformat(timespec="minutes"),
        "timezone": timezone_info.key,
    }

    schedule_terms = (
        "today", "tomorrow", "yesterday", "tonight", "this week", "next week",
        "event", "schedule", "exam", "meeting", "appointment", "deadline",
        "what do i have", "when is",
    )
    if any(term in text for term in schedule_terms):
        window = _date_window(text, local_now.date())
        if window is None:
            start, end, label = local_now.date(), local_now.date() + timedelta(days=7), "upcoming"
        else:
            start, end, label = window
        events = _matching_events(db, start, end)
        context["events"] = {
            "period": label,
            "records": [
                {
                    "title": event.title,
                    "date": event.date.isoformat(),
                    "time": event.time.isoformat(timespec="minutes") if event.time else None,
                    "event_type": event.event_type,
                    "location": event.location,
                    "status": event.status,
                }
                for event in events
            ],
        }

    task_terms = ("task", "to-do", "todo", "what should i do", "left to do", "unfinished")
    if any(term in text for term in task_terms):
        tasks = (
            db.query(Task)
            .filter(Task.completed.is_(False))
            .order_by(Task.id.desc())
            .limit(25)
            .all()
        )
        context["open_tasks"] = [
            {"title": task.title, "notes": task.description}
            for task in tasks
        ]
        context["task_due_dates_available"] = False

    if any(term in text for term in ("my goal", "my goals", "learning", "study", "prefer")):
        profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
        if profile:
            context["relevant_profile"] = {
                "preferred_name": profile.preferred_name or profile.name,
                "communication_style": profile.communication_style,
                "learning_goals": profile.learning_goals,
                "personal_goals": profile.personal_goals,
            }

    return json.dumps(context, ensure_ascii=False)