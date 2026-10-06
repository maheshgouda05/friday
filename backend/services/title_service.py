import re

from backend.services.ai_service import AIServiceError, generate_conversation_title


_FALLBACK_STOP_WORDS = {
    "a", "about", "after", "am", "an", "and", "are", "at", "be", "can",
    "could", "do", "for", "from", "get", "have", "help", "how", "i", "in",
    "is", "it", "me", "my", "need", "of", "on", "please", "should", "the",
    "to", "want", "what", "when", "where", "with", "would", "you", "your",
    "today", "tomorrow", "yesterday", "tonight", "morning", "evening",
}


def fallback_title(message: str) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", message)
    keywords = [word for word in words if word.lower() not in _FALLBACK_STOP_WORDS]
    if not keywords:
        text = message.lower()
        if "tomorrow" in text:
            return "Tomorrow Schedule"
        if "today" in text or "tonight" in text:
            return "Today Schedule"
        return "General Conversation"
    if len(keywords) == 1:
        if keywords[0].lower() in {"event", "events", "exam", "meeting", "schedule"}:
            keywords.append("Planning")
        else:
            return "General Conversation"

    title_words = keywords[:4]
    title = " ".join(
        word if word.isupper() else word[0].upper() + word[1:].lower()
        for word in title_words
    )
    normalized_title = " ".join(re.findall(r"[a-z0-9]+", title.lower()))
    normalized_message = " ".join(re.findall(r"[a-z0-9]+", message.lower()))
    if normalized_title == normalized_message:
        title = f"{title} Discussion"
    return title


def generate_title(message: str) -> str:
    try:
        title = generate_conversation_title(message)
        words = title.split()
        cleaned_title = title.strip(" \"'`.:;-")[:120]
        normalized_title = " ".join(re.findall(r"[a-z0-9]+", cleaned_title.lower()))
        normalized_message = " ".join(re.findall(r"[a-z0-9]+", message.lower()))
        if 2 <= len(words) <= 5 and normalized_title != normalized_message:
            return cleaned_title or fallback_title(message)
    except AIServiceError:
        pass
    return fallback_title(message)