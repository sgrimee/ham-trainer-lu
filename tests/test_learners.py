"""Learner identity (specs/LEARN.md §6, phase 2): the account store and its
§8.1 plumbing, the command line, the password-guarded /admin pages and the
/learn name picker."""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import threading

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import admin, learners
from app.main import LEARNER_COOKIE
from app.store import AccountExists, Store

PASSWORD = "s3cret-é"   # non-ASCII on purpose: compare_digest on str would raise


@pytest.fixture(autouse=True)
def admin_env(monkeypatch):
    """Tests must not see the developer's .env (mise autoloads it), and the
    rate limiter is process-global state."""
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_FILE", raising=False)
    admin.limiter.reset()
    yield
    admin.limiter.reset()


@pytest.fixture
def with_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)


AUTH = ("anyone", PASSWORD)


# -- store ----------------------------------------------------------------------

def test_store_uses_wal(store: Store):
    with sqlite3.connect(store.path) as con:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_write_tx_rolls_back_on_exception(store: Store):
    with pytest.raises(RuntimeError):
        with store._write_tx() as con:
            con.execute("INSERT INTO account (id, display_name, created_at) VALUES ('x', 'X', 'now')")
            raise RuntimeError("boom")
    assert store.get_account("x") is None


def test_write_tx_serializes_writers(store: Store):
    """BEGIN IMMEDIATE takes the write lock up front: a second transaction
    waits for the first instead of reading stale state (§8.1 guard 1)."""
    order: list[str] = []
    first_in = threading.Event()

    def first():
        with store._write_tx() as con:
            first_in.set()
            con.execute("SELECT 1")
            threading.Event().wait(0.3)
            order.append("first")

    t = threading.Thread(target=first)
    t.start()
    first_in.wait()
    with store._write_tx():
        order.append("second")
    t.join()
    assert order == ["first", "second"]


def test_create_account_normalises_and_refuses_duplicates(store: Store):
    account_id = store.create_account("  Léa   M ")
    account = store.get_account(account_id)
    assert account is not None and account["display_name"] == "Léa M"
    with pytest.raises(AccountExists):
        store.create_account("Léa M")
    with pytest.raises(ValueError):
        store.create_account("   ")
    with pytest.raises(ValueError):
        store.create_account("x" * 41)


def test_delete_account_removes_all_progress(store: Store):
    keep = store.create_account("Keep")
    gone = store.create_account("Gone")
    with store._connect() as con:
        for account_id in (keep, gone):
            con.execute("INSERT INTO step_progress VALUES (?, 'charge', 'now')", (account_id,))
            con.execute("INSERT INTO practice_result (account_id, question_id, updated_at) "
                        "VALUES (?, 15, 'now')", (account_id,))
            con.execute("INSERT INTO award VALUES (?, 'xp', 'q15', 10, 'now', NULL)", (account_id,))
    assert store.account_summary(gone) == {"steps_completed": 1, "xp": 10, "badges": 0}

    assert store.delete_account(gone) is True
    assert store.get_account(gone) is None
    with store._connect() as con:
        for table in ("step_progress", "practice_result", "award"):
            ids = {r[0] for r in con.execute(f"SELECT account_id FROM {table}")}
            assert ids == {keep}, table
    assert store.delete_account(gone) is False


# -- command line -----------------------------------------------------------------

def test_command_line(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATTEMPTS_DB", str(tmp_path / "cli.db"))
    assert learners.main(["add", "Léa Martin"]) == 0
    assert learners.main(["add", "Léa Martin"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert learners.main(["list"]) == 0
    assert "Léa Martin" in capsys.readouterr().out
    assert learners.main(["delete", "Nobody"]) == 1
    assert learners.main(["delete", "Léa Martin"]) == 0
    assert Store(tmp_path / "cli.db").accounts() == []


# -- admin password (§6.1.1) ---------------------------------------------------------

def test_admin_is_404_without_a_password(client):
    assert client.get("/admin/learners").status_code == 404
    assert client.get("/admin/learners", auth=AUTH).status_code == 404
    # Not 422: the guard runs before the form is validated.
    assert client.post("/admin/learners").status_code == 404


def test_admin_empty_password_is_disabled(client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    assert client.get("/admin/learners").status_code == 404


def test_admin_needs_the_password(client, with_password):
    resp = client.get("/admin/learners")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"].startswith("Basic")
    assert client.get("/admin/learners", auth=("admin", "wrong")).status_code == 401
    resp = client.get("/admin/learners", auth=AUTH)
    assert resp.status_code == 200
    assert "noindex" in resp.headers["x-robots-tag"]
    assert '<meta name="robots" content="noindex' in resp.text


def test_admin_password_file_wins(client, monkeypatch, tmp_path):
    secret = tmp_path / "admin_password"
    secret.write_text("from-file\n")
    monkeypatch.setenv("ADMIN_PASSWORD", "from-env")
    monkeypatch.setenv("ADMIN_PASSWORD_FILE", str(secret))
    assert client.get("/admin/learners", auth=("a", "from-env")).status_code == 401
    assert client.get("/admin/learners", auth=("a", "from-file")).status_code == 200


def test_unreadable_password_file_stops_startup(monkeypatch, tmp_path):
    from starlette.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("ADMIN_PASSWORD_FILE", str(tmp_path / "missing"))
    with pytest.raises(admin.AdminConfigError, match="ADMIN_PASSWORD_FILE"), TestClient(app):
        pass


def test_admin_refuses_cross_site_posts(client, store: Store, with_password):
    account_id = store.create_account("Léa")
    url = f"/admin/learners/{account_id}/delete"
    for headers in ({"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"},
                    {"Origin": "http://evil.example"}, {"Origin": "null"}):
        resp = client.post(url, auth=AUTH, headers=headers, follow_redirects=False)
        assert resp.status_code == 403, headers
    assert store.get_account(account_id) is not None
    # A cross-site GET changes nothing and is allowed (a link to the page).
    assert client.get("/admin/learners", auth=AUTH,
                      headers={"Sec-Fetch-Site": "cross-site"}).status_code == 200
    # The admin's own form: same origin.
    resp = client.post(url, auth=AUTH, follow_redirects=False,
                       headers={"Sec-Fetch-Site": "same-origin", "Origin": "http://testserver"})
    assert resp.status_code == 303
    assert store.get_account(account_id) is None


def test_admin_origin_check_without_fetch_metadata(client, with_password):
    resp = client.post("/admin/learners", data={"display_name": "Tom"}, auth=AUTH,
                       headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert resp.status_code == 303


def test_admin_rate_limit(client, with_password):
    for _ in range(admin.MAX_FAILURES):
        assert client.get("/admin/learners", auth=("a", "wrong")).status_code == 401
    # Locked out: even the right password is refused.
    assert client.get("/admin/learners", auth=AUTH).status_code == 429


def test_admin_missing_credentials_do_not_count(client, with_password):
    for _ in range(admin.MAX_FAILURES + 2):
        assert client.get("/admin/learners").status_code == 401
    assert client.get("/admin/learners", auth=AUTH).status_code == 200


def test_rate_limit_window_expires(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(admin.time, "monotonic", lambda: clock[0])
    limiter = admin.FailureLimiter(max_failures=2, window=60)
    limiter.record_failure("c")
    limiter.record_failure("c")
    assert limiter.blocked("c") and not limiter.blocked("other")
    clock[0] += 60
    assert not limiter.blocked("c")


# -- admin pages (§6.1) --------------------------------------------------------------

def test_admin_add_list_and_delete(client, store: Store, with_password):
    resp = client.post("/admin/learners", data={"display_name": "Léa"}, auth=AUTH,
                       follow_redirects=False)
    assert resp.status_code == 303
    assert "Léa" in client.get("/admin/learners", auth=AUTH).text

    resp = client.post("/admin/learners", data={"display_name": "Léa"}, auth=AUTH)
    assert resp.status_code == 200
    assert "existe déjà" in resp.text
    assert len(store.accounts()) == 1

    account_id = store.accounts()[0]["id"]
    confirm = client.get(f"/admin/learners/{account_id}/delete", auth=AUTH)
    assert confirm.status_code == 200 and "Supprimer Léa" in confirm.text
    assert store.get_account(account_id) is not None   # the GET deletes nothing

    resp = client.post(f"/admin/learners/{account_id}/delete", auth=AUTH, follow_redirects=False)
    assert resp.status_code == 303
    assert store.accounts() == []


def test_admin_blank_name_is_a_message(client, store: Store, with_password):
    resp = client.post("/admin/learners", data={"display_name": "  "}, auth=AUTH)
    assert resp.status_code == 200
    assert store.accounts() == []


def test_admin_delete_unknown_redirects(client, with_password):
    resp = client.get("/admin/learners/nope/delete", auth=AUTH, follow_redirects=False)
    assert resp.status_code == 303


# -- the name picker (§6.1) ------------------------------------------------------------

def test_learn_with_no_accounts(client):
    resp = client.get("/learn")
    assert resp.status_code == 200
    assert "<select" not in resp.text


def test_pick_a_name_then_change(client, store: Store):
    account_id = store.create_account("Léa")
    store.create_account("Max")
    picker = client.get("/learn")
    assert "Léa" in picker.text and "Max" in picker.text

    resp = client.post("/learn/who", data={"account_id": account_id}, follow_redirects=False)
    assert resp.status_code == 303
    assert client.cookies.get(LEARNER_COOKIE) == account_id
    page = client.get("/learn")
    assert "Bonjour Léa" in page.text and "/learn/who/clear" in page.text

    client.post("/learn/who/clear")
    assert client.cookies.get(LEARNER_COOKIE) is None
    assert "<select" in client.get("/learn").text


def test_unknown_account_is_not_picked(client, store: Store):
    store.create_account("Léa")
    client.post("/learn/who", data={"account_id": "forged"})
    assert client.cookies.get(LEARNER_COOKIE) is None


def test_deleted_learner_goes_back_to_the_picker(client, store: Store):
    account_id = store.create_account("Léa")
    client.post("/learn/who", data={"account_id": account_id})
    store.delete_account(account_id)
    resp = client.get("/learn")
    assert resp.status_code == 200
    assert "Qui es-tu" in resp.text
    assert client.cookies.get(LEARNER_COOKIE) is None   # the stale cookie is cleared


def test_admin_malformed_authorization_is_401(client, with_password):
    for header in ("Basic !!!", "Basic " + "bm9jb2xvbg==", "Bearer xyz"):   # bad b64, no colon, other scheme
        assert client.get("/admin/learners", headers={"Authorization": header}).status_code == 401
    assert client.get("/admin/learners", auth=AUTH).status_code == 200   # none of them counted
