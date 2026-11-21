"""Persistent local reminders for JARVIS EXE; alerts exactly 10 minutes early."""
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

class ReminderManager:
    def __init__(self, storage_path):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.items = []
        self.load()

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = raw if isinstance(raw, list) else []
        except Exception:
            self.items = []

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, title, when):
        item = {
            "id": uuid.uuid4().hex,
            "title": title[:160],
            "when": when.isoformat(timespec="minutes"),
            "notify_at": (when - timedelta(minutes=10)).isoformat(timespec="minutes"),
            "notified": False,
            "created": datetime.now().isoformat(timespec="seconds")
        }
        self.items.append(item)
        self.save()
        return item

    def due(self, now=None):
        now = now or datetime.now()
        due_items = []
        changed = False
        for item in self.items:
            if item.get("notified") or item.get("cancelled"):
                continue
            try:
                notify_at = datetime.fromisoformat(item["notify_at"])
                event_at = datetime.fromisoformat(item["when"])
            except Exception:
                continue
            if notify_at <= now < event_at + timedelta(minutes=1):
                item["notified"] = True
                due_items.append(item.copy())
                changed = True
        if changed:
            self.save()
        return due_items

    def upcoming(self, limit=10):
        now = datetime.now()
        result = []
        for item in self.items:
            try:
                when = datetime.fromisoformat(item["when"])
            except Exception:
                continue
            if when >= now and not item.get("cancelled"):
                result.append((when, item))
        return [item for _, item in sorted(result)[:limit]]

    def cancel(self, reminder_id):
        for item in self.items:
            if item.get("id") == reminder_id:
                item["cancelled"] = True
                self.save()
                return True
        return False

def parse_reminder(text, now=None):
    """Parse simple pt-BR reminders like 'me avisa da reunião às 15h'."""
    now = now or datetime.now()
    match = re.search(r"\b(?:(?:às?|as)\s*)?(\d{1,2})(?::(\d{2}))?\s*h?\b", text, re.I)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    if hour > 23 or minute > 59:
        return None
    day = now.date()
    if re.search(r"\bamanh[ãa]\b", text, re.I):
        day += timedelta(days=1)
    elif re.search(r"\bdepois de amanhã\b", text, re.I):
        day += timedelta(days=2)
    when = datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)
    if when <= now and day == now.date():
        return None
    title = re.sub(r"^\s*(?:jarvis[, ]*)?(?:me\s+)?(?:avisa|lembra|lembre-me|me\s+lembre|marca|agende)\s*(?:de|da|do|sobre)?\s*", "", text, flags=re.I)
    title = re.sub(r"\b(?:amanh[ãa]|depois de amanhã)\b", "", title, flags=re.I)
    title = re.sub(r"\b(?:às?\s*)?\d{1,2}(?::\d{2})?\s*h?\b", "", title, flags=re.I)
    title = re.sub(r"\b(?:por favor|pra mim|para mim|não esquecer|nao esquecer)\b", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" ,.!?")
    if not title:
        title = "Compromisso"
    return title[:160], when
