# Task 1 Report: Pure helpers `remaining_days` + notification copy (+ pytest bootstrap)

**Status:** DONE  
**Branch:** `feat/web-push-filter-reminder`  
**Commit:** `3726e8e` — feat: add remaining_days helper for filter due push  
**Date:** 2026-07-24

---

## Summary

Implemented pure helper functions for computing filter remaining days and building Vietnamese notification copy, plus pytest bootstrap for the backend test suite. All changes follow the plan brief verbatim.

---

## TDD Steps Executed

### Step 1: Add test deps + pytest.ini

- Appended to `requirements.txt`:
  - `apscheduler==3.10.4`
  - `pywebpush==2.0.1`
  - `pytest==8.3.4`
  - `httpx==0.28.1`
- Created `pytest.ini` with `testpaths = tests` and `pythonpath = .`

### Step 2: Write failing tests

- Created `tests/test_filter_remaining.py` with 5 tests (exact code from brief)

### Step 3: Run tests — expect FAIL

```
ModuleNotFoundError: No module named 'app.services.filter_remaining'
```

Command used: `.\venv\Scripts\python.exe -m pytest tests/test_filter_remaining.py -v`

### Step 4: Implement helpers

- Created `app/services/filter_remaining.py` with:
  - `compute_remaining_days(last_replaced_date, lifespan_days, today=None) -> int`
  - `build_filter_due_copy(filter_name, purifier_name, remaining_days) -> tuple[str, str]`

### Step 5: Run tests — expect PASS

```
5 passed in 0.05s
```

All tests:
- `test_remaining_days_basic` — 150 days remaining
- `test_remaining_days_at_threshold` — exactly 30 days (notification threshold)
- `test_remaining_days_overdue` — -9 days overdue
- `test_copy_remaining` — Vietnamese copy for positive remaining days
- `test_copy_overdue` — Vietnamese copy for overdue filters

### Step 6: Commit

```
3726e8e feat: add remaining_days helper for filter due push
 4 files changed, 63 insertions(+)
 - app/services/filter_remaining.py (new)
 - pytest.ini (new)
 - tests/test_filter_remaining.py (new)
 - requirements.txt (modified)
```

---

## Files Changed

| File | Action |
|---|---|
| `app/services/filter_remaining.py` | Created |
| `tests/test_filter_remaining.py` | Created |
| `pytest.ini` | Created |
| `requirements.txt` | Modified (4 deps appended) |

No other files were modified. Frontend, docs, and unrelated backend files untouched.

---

## Self-Review

### Correctness

- `compute_remaining_days` formula: `lifespan_days - (as_of - last_replaced_date).days` — matches plan and existing business logic pattern.
- `build_filter_due_copy` uses exact Vietnamese strings from spec:
  - Title: `Nhắc thay lõi lọc`
  - Body còn hạn / quá hạn with correct quoting and em-dash
- Edge case `remaining_days == 0` uses the "còn hạn" branch (not `< 0`), consistent with threshold `<= 30` in plan.

### Code Quality

- Minimal scope: two pure functions, no side effects, no DB/API dependencies.
- Uses `from __future__ import annotations` for `date | None` syntax (consistent with existing backend).
- Testable via injectable `today` parameter — no flaky date-dependent tests.

### Conventions

- Placed in `app/services/` per file map in plan.
- Test file naming `test_filter_remaining.py` matches module name.
- Commit message follows repo style (`feat:` prefix).

### Concerns (minor)

1. **Git commit tooling:** Shell-injected `--trailer` flag is unsupported on git 2.27; commit succeeded via Python subprocess. No impact on repo state.
2. **System Python vs venv:** Global `pip install -r requirements.txt` failed on `psycopg2-binary` (32-bit Python 3.8). Tests run correctly in project `venv`. Future CI should use venv or Docker.
3. **Future task deps:** `apscheduler` and `pywebpush` added early (per plan) but unused until later tasks — intentional per Task 1 brief.

---

## Verification Commands

```powershell
cd src/water-purifier-management-backend
.\venv\Scripts\python.exe -m pip install pytest==8.3.4 httpx==0.28.1 apscheduler==3.10.4 pywebpush==2.0.1
.\venv\Scripts\python.exe -m pytest tests/test_filter_remaining.py -v
```

Expected: **5 passed**

---

## Ready for Task 2

Helpers are pure and tested. Task 2 can add `PushSubscription` / `Notification` entities and Alembic migration without changes to this module.
