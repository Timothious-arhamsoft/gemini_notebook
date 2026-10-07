"""Unit tests for registration field validation (no DNS/MX)."""

import pytest
from pydantic import ValidationError

from app.auth_validation import (
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    validate_email_address,
    validate_full_name,
    validate_password,
    validate_username,
)
from app.routers.auth import UserRegister


# ── Email ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "email",
    [
        "abc@example.com",
        "john@gmail.com",
        "abc@fake-domain.test",
        "user.name+tag@sub.example.co.uk",
    ],
)
def test_email_valid_syntax(email: str):
    assert "@" in validate_email_address(email)


@pytest.mark.parametrize(
    "email",
    [
        "abc",
        "@example.com",
        "abc@",
        "abc@@example.com",
        "@",
        "",
        "   ",
    ],
)
def test_email_invalid_syntax(email: str):
    with pytest.raises(ValueError, match="valid email"):
        validate_email_address(email)


def test_email_is_normalized():
    assert validate_email_address("John.Doe@Gmail.COM") == "john.doe@gmail.com"


def test_email_duplicate_casing_collapses():
    assert validate_email_address("User@Example.com") == validate_email_address(
        "user@example.com"
    )


# ── Full name ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "name",
    ["Tim Cook", "Mary Jane", "O'Connor", "Anne-Marie", "José García"],
)
def test_full_name_valid(name: str):
    assert validate_full_name(name) == name.strip()


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_full_name_empty_or_whitespace(name: str):
    with pytest.raises(ValueError, match="full name"):
        validate_full_name(name)


def test_full_name_is_trimmed():
    assert validate_full_name("  Tim Cook  ") == "Tim Cook"


def test_full_name_rejects_too_long():
    with pytest.raises(ValueError, match="at most"):
        validate_full_name("x" * 256)


# ── Username ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "username,expected",
    [
        ("timcook", "timcook"),
        ("TimCook", "timcook"),
        ("user_1", "user_1"),
        ("abc", "abc"),
    ],
)
def test_username_valid(username: str, expected: str):
    assert validate_username(username) == expected


@pytest.mark.parametrize(
    "username",
    [
        "",
        "   ",
        "ab",  # too short
        "a" * (USERNAME_MAX_LENGTH + 1),
        "bad-name",
        "has space",
        "weird!",
    ],
)
def test_username_invalid(username: str):
    with pytest.raises(ValueError):
        validate_username(username)


def test_username_length_bounds_in_message():
    with pytest.raises(
        ValueError,
        match=f"between {USERNAME_MIN_LENGTH} and {USERNAME_MAX_LENGTH}",
    ):
        validate_username("ab")


# ── Password ────────────────────────────────────────────────

def test_password_min_length_valid():
    assert validate_password("a" * PASSWORD_MIN_LENGTH) == "a" * PASSWORD_MIN_LENGTH


def test_password_preserves_internal_and_edge_spaces():
    # Leading/trailing spaces are allowed if the password is not *only* whitespace
    assert validate_password("  secret  ") == "  secret  "


def test_password_too_short():
    with pytest.raises(ValueError, match=f"at least {PASSWORD_MIN_LENGTH}"):
        validate_password("12345")


def test_password_whitespace_only_rejected():
    with pytest.raises(ValueError, match="whitespace"):
        validate_password("      ")


def test_password_empty_rejected():
    with pytest.raises(ValueError, match=f"at least {PASSWORD_MIN_LENGTH}"):
        validate_password("")


# ── UserRegister schema ─────────────────────────────────────

def test_user_register_valid_payload():
    payload = UserRegister(
        full_name="Tim Cook",
        username="timcook",
        email="abc@example.com",
        password="valid-password",
    )
    assert payload.full_name == "Tim Cook"
    assert payload.username == "timcook"
    assert payload.email == "abc@example.com"
    assert payload.password == "valid-password"


def test_user_register_rejects_missing_full_name():
    with pytest.raises(ValidationError):
        UserRegister(
            full_name="",
            username="timcook",
            email="abc@example.com",
            password="valid-password",
        )


def test_user_register_rejects_bad_email():
    with pytest.raises(ValidationError):
        UserRegister(
            full_name="Tim Cook",
            username="timcook",
            email="abc",
            password="valid-password",
        )
