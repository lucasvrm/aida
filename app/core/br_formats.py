import re
import unicodedata
from datetime import date, datetime

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def normalize_header(s: str) -> str:
    s = s or ""
    s = s.replace("\u00a0", " ")
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = strip_accents(s).lower()
    s = re.sub(r"[^\w\s%/().-]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

_money_re = re.compile(r"-?\s*(?:r\$\s*)?([\d\.]+(?:,\d{1,2})?)", re.IGNORECASE)

def parse_brl_money(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s == "":
        return None
    s = s.replace("\u00a0", " ")
    m = _money_re.search(s)
    if not m:
        return None
    num = m.group(1)
    num = num.replace(".", "").replace(",", ".")
    try:
        return float(num)
    except Exception:
        return None

def parse_int(val) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    s = str(val).strip()
    if s == "":
        return None
    s = re.sub(r"[^\d-]+", "", s)
    try:
        return int(s)
    except Exception:
        return None

def parse_float(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s == "":
        return None
    s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^\d\.-]+", "", s)
    try:
        return float(s)
    except Exception:
        return None

def parse_date_br(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    if s == "":
        return None

    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except Exception:
            return None

    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except Exception:
            return None

    return None

def only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def is_valid_cpf(cpf: str) -> bool:
    cpf = only_digits(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    nums = list(map(int, cpf))
    for j in [9, 10]:
        s = sum(nums[i] * ((j + 1) - i) for i in range(j))
        d = (s * 10) % 11
        d = 0 if d == 10 else d
        if d != nums[j]:
            return False
    return True

def is_valid_cnpj(cnpj: str) -> bool:
    cnpj = only_digits(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    nums = list(map(int, cnpj))
    weights1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    weights2 = [6] + weights1
    def calc_digit(weights):
        s = sum(nums[i] * weights[i] for i in range(len(weights)))
        r = s % 11
        return 0 if r < 2 else 11 - r
    d1 = calc_digit(weights1)
    d2 = calc_digit(weights2)
    return d1 == nums[12] and d2 == nums[13]
