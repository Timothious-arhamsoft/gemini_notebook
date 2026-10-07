"""Registration endpoint tests: duplicates, integrity races, happy path."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.routers.auth import UserRegister, register


def _payload(**overrides):
    data = {
        "full_name": "Tim Cook",
        "username": "timcook",
        "email": "abc@example.com",
        "password": "valid-password",
    }
    data.update(overrides)
    return UserRegister(**data)


def _mock_db(*, email_exists=False, username_exists=False, commit_error=None):
    db = MagicMock()

    def filter_side_effect(*_args, **_kwargs):
        result = MagicMock()
        # First filter().first() is email check; second is username check
        # Track calls via a list on the mock
        return result

    query = MagicMock()
    email_q = MagicMock()
    username_q = MagicMock()
    email_q.first.return_value = object() if email_exists else None
    username_q.first.return_value = object() if username_exists else None

    # query(User).filter(...).first() — alternate by call order
    calls = {"n": 0}

    def filter_impl(*_a, **_k):
        calls["n"] += 1
        return email_q if calls["n"] == 1 else username_q

    query.filter.side_effect = filter_impl
    db.query.return_value = query

    if commit_error is not None:
        db.commit.side_effect = commit_error
    return db


def test_register_success_hashes_password_and_commits():
    db = _mock_db()
    with patch("app.routers.auth.pwd_ctx") as pwd:
        pwd.hash.return_value = "hashed-valid-password"
        user = register(_payload(), db)

    pwd.hash.assert_called_once_with("valid-password")
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.email == "abc@example.com"
    assert added.username == "timcook"
    assert added.full_name == "Tim Cook"
    assert added.hashed_password == "hashed-valid-password"
    assert user is added


def test_register_rejects_duplicate_email():
    db = _mock_db(email_exists=True)
    with pytest.raises(HTTPException) as exc:
        register(_payload(), db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already registered."
    db.add.assert_not_called()


def test_register_rejects_duplicate_username():
    db = _mock_db(username_exists=True)
    with pytest.raises(HTTPException) as exc:
        register(_payload(username="takenuser", email="other@example.com"), db)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Username already taken."
    db.add.assert_not_called()


def test_register_integrity_error_email_maps_cleanly():
    err = IntegrityError(
        "INSERT",
        {},
        Exception('duplicate key value violates unique constraint "users_email_key"'),
    )
    db = _mock_db(commit_error=err)
    with patch("app.routers.auth.pwd_ctx") as pwd:
        pwd.hash.return_value = "hashed"
        with pytest.raises(HTTPException) as exc:
            register(_payload(), db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already registered."
    db.rollback.assert_called_once()


def test_register_integrity_error_username_maps_cleanly():
    err = IntegrityError(
        "INSERT",
        {},
        Exception('duplicate key value violates unique constraint "users_username_key"'),
    )
    db = _mock_db(commit_error=err)
    with patch("app.routers.auth.pwd_ctx") as pwd:
        pwd.hash.return_value = "hashed"
        with pytest.raises(HTTPException) as exc:
            register(_payload(), db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Username already taken."
    db.rollback.assert_called_once()
