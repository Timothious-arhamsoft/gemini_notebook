"""Shared registration/login field validation (syntax only — no DNS/MX)."""

from __future__ import annotations

import re

from email_validator import EmailNotValidError, validate_email

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 100  # matches users.username VARCHAR(100)
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")

FULL_NAME_MAX_LENGTH = 255  # matches users.full_name VARCHAR(255)

PASSWORD_MIN_LENGTH = 6  # matches existing frontend minLength={6}


def validate_email_address(value: str) -> str:
    """
    Require a reasonable email structure. No DNS/MX/domain-existence checks.

    test_environment=True allows structurally valid reserved TLDs like .test.
    """
    if value is None or not str(value).strip():
        raise ValueError("Please enter a valid email address.")

    try:
        result = validate_email(
            str(value).strip(),
            check_deliverability=False,
            test_environment=True,
        )
    except EmailNotValidError as exc:
        raise ValueError("Please enter a valid email address.") from exc

    # Lowercase full address so duplicate checks are case-insensitive
    # (email-validator only lowercases the domain by default).
    return result.normalized.lower()


def validate_username(value: str) -> str:
    if value is None:
        raise ValueError("Please enter a username.")

    username = str(value).strip()
    if not username:
        raise ValueError("Please enter a username.")

    if len(username) < USERNAME_MIN_LENGTH or len(username) > USERNAME_MAX_LENGTH:
        raise ValueError(
            f"Username must be between {USERNAME_MIN_LENGTH} and "
            f"{USERNAME_MAX_LENGTH} characters."
        )

    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username may only contain letters, numbers, and underscores."
        )

    return username.lower()


def validate_full_name(value: str) -> str:
    if value is None:
        raise ValueError("Please enter your full name.")

    full_name = str(value).strip()
    if not full_name:
        raise ValueError("Please enter your full name.")

    if len(full_name) > FULL_NAME_MAX_LENGTH:
        raise ValueError(
            f"Full name must be at most {FULL_NAME_MAX_LENGTH} characters."
        )

    return full_name


def validate_password(value: str) -> str:
    """Validate password. Do not trim — whitespace may be intentional."""
    if value is None or value == "":
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )

    if not isinstance(value, str):
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )

    if value.strip() == "":
        raise ValueError("Password cannot be only whitespace.")

    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )

    return value
