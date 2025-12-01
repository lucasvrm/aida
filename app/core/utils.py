import re
from uuid import UUID

def is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except Exception:
        return False

def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r'[^a-zA-Z0-9 _\-\.\(\)\[\]]+', "_", name)
    return name[:180] if len(name) > 180 else name

def normalize_whitespace(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()
