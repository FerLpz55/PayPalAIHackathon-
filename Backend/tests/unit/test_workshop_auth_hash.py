import bcrypt
import pytest

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.infrastructure.security.workshop_auth import (
    ensure_workshop_auth_configured,
    is_valid_password_hash,
)
from tallerclaro.presentation.http.dependencies import _verify_workshop_credentials


def test_workshop_auth_uses_hash_and_rejects_invalid_configuration():
    hashed = bcrypt.hashpw(b"correct-password", bcrypt.gensalt(rounds=4)).decode()
    settings = Settings(workshop_username="shop", workshop_password_hash=hashed)
    assert _verify_workshop_credentials("shop", "correct-password", settings)
    assert not _verify_workshop_credentials("shop", "wrong", settings)
    assert not _verify_workshop_credentials("shop", "demo-password", Settings(workshop_username="shop"))


def test_startup_and_authentication_share_hash_validation():
    hashed = bcrypt.hashpw(b"correct-password", bcrypt.gensalt(rounds=4)).decode()
    valid = Settings(workshop_username="shop", workshop_password_hash=hashed)

    assert is_valid_password_hash(hashed)
    ensure_workshop_auth_configured(valid)

    for invalid_hash in ("", "not-a-bcrypt-hash", "$2b$12$too-short"):
        assert is_valid_password_hash(invalid_hash) is False
        with pytest.raises(RuntimeError, match="bcrypt"):
            ensure_workshop_auth_configured(
                Settings(workshop_username="shop", workshop_password_hash=invalid_hash)
            )
        assert not _verify_workshop_credentials(
            "shop",
            "correct-password",
            Settings(workshop_username="shop", workshop_password_hash=invalid_hash),
        )
