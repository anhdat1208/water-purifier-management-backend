### Task 1: Pure helpers `remaining_days` + notification copy (+ pytest bootstrap)

**Files:**
- Create: `src/water-purifier-management-backend/app/services/filter_remaining.py`
- Create: `src/water-purifier-management-backend/tests/test_filter_remaining.py`
- Create: `src/water-purifier-management-backend/pytest.ini`
- Modify: `src/water-purifier-management-backend/requirements.txt`

**Interfaces:**
- Consumes: `datetime.date`
- Produces:
  - `compute_remaining_days(last_replaced_date: date, lifespan_days: int, today: date | None = None) -> int`
  - `build_filter_due_copy(filter_name: str, purifier_name: str, remaining_days: int) -> tuple[str, str]`  # (title, body)

- [ ] **Step 1: Add test deps + pytest.ini**

Append to `requirements.txt`:

```text
apscheduler==3.10.4
pywebpush==2.0.1
pytest==8.3.4
httpx==0.28.1
```

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_filter_remaining.py
from datetime import date

from app.services.filter_remaining import build_filter_due_copy, compute_remaining_days


def test_remaining_days_basic():
    assert compute_remaining_days(date(2026, 1, 1), 180, today=date(2026, 1, 31)) == 150


def test_remaining_days_at_threshold():
    assert compute_remaining_days(date(2026, 1, 1), 180, today=date(2026, 5, 31)) == 30


def test_remaining_days_overdue():
    assert compute_remaining_days(date(2026, 1, 1), 10, today=date(2026, 1, 20)) == -9


def test_copy_remaining():
    title, body = build_filter_due_copy("Lõi RO", "Máy bếp", 12)
    assert title == "Nhắc thay lõi lọc"
    assert body == 'Lõi "Lõi RO" trên máy "Máy bếp" còn 12 ngày — nên thay sớm.'


def test_copy_overdue():
    title, body = build_filter_due_copy("Lõi RO", "Máy bếp", -3)
    assert title == "Nhắc thay lõi lọc"
    assert body == 'Lõi "Lõi RO" trên máy "Máy bếp" đã quá hạn 3 ngày — cần thay ngay.'
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd src/water-purifier-management-backend
pip install -r requirements.txt
pytest tests/test_filter_remaining.py -v
```

Expected: `ModuleNotFoundError` / import error for `filter_remaining`.

- [ ] **Step 4: Implement helpers**

```python
# app/services/filter_remaining.py
from __future__ import annotations

from datetime import date


def compute_remaining_days(
    last_replaced_date: date,
    lifespan_days: int,
    today: date | None = None,
) -> int:
    as_of = today or date.today()
    return lifespan_days - (as_of - last_replaced_date).days


def build_filter_due_copy(filter_name: str, purifier_name: str, remaining_days: int) -> tuple[str, str]:
    title = "Nhắc thay lõi lọc"
    if remaining_days < 0:
        body = (
            f'Lõi "{filter_name}" trên máy "{purifier_name}" '
            f"đã quá hạn {abs(remaining_days)} ngày — cần thay ngay."
        )
    else:
        body = (
            f'Lõi "{filter_name}" trên máy "{purifier_name}" '
            f"còn {remaining_days} ngày — nên thay sớm."
        )
    return title, body
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/test_filter_remaining.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit (backend repo)**

```bash
cd src/water-purifier-management-backend
git add requirements.txt pytest.ini app/services/filter_remaining.py tests/test_filter_remaining.py
git commit -m "feat: add remaining_days helper for filter due push"
```

---

