import datetime
import re
from config import FIELDS, LABELS

def format_note(data):
    """Format entered facts only; blank encounters produce no clinical content."""
    from note_workflow import build_note_body, approve_note
    body = build_note_body(data)
    return approve_note(body).text if body else ''

def parse_dictation(text, data):
    updated = []
    unlabelled = []
    field_names = sorted(
        {alias for aliases in LABELS.values() for alias in aliases},
        key=len,
        reverse=True,
    )
    field_pattern = "|".join(re.escape(alias) for alias in field_names)
    separator = r"(?<=[.!?])\s+|\s*[;\n]+\s*|,\s*(?=(?:" + field_pattern + r")(?:\s*[:：\-]|\s))"
    parts = re.split(separator, text, flags=re.IGNORECASE)
    for raw_line in parts:
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for key, aliases in LABELS.items():
            for alias in sorted(aliases, key=len, reverse=True):
                match = re.match(
                    r"^\s*"
                    + re.escape(alias)
                    + r"(?:\s*[:：,\-]\s*|\s+)(.*?)\s*$",
                    line,
                    re.IGNORECASE,
                )
                if match and match.group(1).strip():
                    data[key] = re.sub(r"[.!?]+$", "", match.group(1).strip()).strip()
                    updated.append(FIELDS[key])
                    matched = True
                    break
            if matched:
                break
        if not matched:
            unlabelled.append(line)
    if unlabelled:
        existing = data["sikayet"].strip()
        additions = "\n".join(unlabelled)
        if existing in ("", "..."):
            data["sikayet"] = additions
        else:
            data["sikayet"] = existing + "\n" + additions
        updated.append(FIELDS["sikayet"] + " (etiketsiz dikte eklendi)")
    return updated
