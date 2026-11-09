"""Configuración: resolución de .env y validaciones estrictas de release."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from tallerclaro.bootstrap import settings as settings_module
from tallerclaro.bootstrap.settings import Settings

BACKEND_ROOT = Path(settings_module.__file__).resolve().parents[3]


def _release_settings(**overrides) -> Settings:
    values = {
        "environment": "release",
        "cors_origins": ["https://taller.example.org"],
        "workshop_password_hash": "$2b$12$" + "a" * 53,
        "customer_token_secret": "s" * 48,
        "paypal_mode": "none",
        "ai_provider": "none",
        "price_lookup_provider": "none",
    }
    values.update(overrides)
    return Settings(**values)


def test_env_file_is_absolute_and_independent_from_cwd():
    assert settings_module.ENV_FILE.is_absolute()
    assert settings_module.ENV_FILE == BACKEND_ROOT / ".env"


def test_dotenv_is_loaded_from_backend_root_regardless_of_cwd(monkeypatch, tmp_path):
    dotenv = tmp_path / "custom.env"
    dotenv.write_text("TALLERCLARO_ENVIRONMENT=test\nTALLERCLARO_APP_NAME=Custom\n")
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=dotenv)
    assert settings.app_name == "Custom"
    assert settings.environment == "test"


def test_process_environment_wins_over_dotenv(monkeypatch, tmp_path):
    dotenv = tmp_path / "custom.env"
    dotenv.write_text("TALLERCLARO_APP_NAME=FromFile\n")
    monkeypatch.setenv("TALLERCLARO_APP_NAME", "FromProcess")
    settings = Settings(_env_file=dotenv)
    assert settings.app_name == "FromProcess"


def test_tests_do_not_load_local_dotenv():
    # El fixture autouse de tests/conftest.py neutraliza Backend/.env.
    assert Settings().database_url is None


@pytest.mark.parametrize("value", ["production", "PROD", "Release"])
def test_environment_aliases_normalize_to_release(value):
    assert _release_settings(environment=value).environment == "release"


@pytest.mark.parametrize("value", ["staging", "qa", ""])
def test_unknown_environment_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(environment=value)


def test_development_allows_defaults():
    assert Settings().environment == "development"
    assert Settings().cors_origins == ["*"]


def test_release_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS"):
        _release_settings(cors_origins=["*"])


def test_release_rejects_http_cors_origin():
    with pytest.raises(ValidationError, match="https"):
        _release_settings(cors_origins=["http://taller.example.org"])


def test_release_rejects_placeholder_workshop_hash():
    with pytest.raises(ValidationError, match="WORKSHOP_PASSWORD_HASH"):
        _release_settings(workshop_password_hash="")


def test_release_rejects_placeholder_customer_secret():
    with pytest.raises(ValidationError, match="CUSTOMER_TOKEN_SECRET"):
        _release_settings(customer_token_secret="change-me-secret-min-32-chars-long")


def test_release_rejects_short_customer_secret():
    with pytest.raises(ValidationError, match="CUSTOMER_TOKEN_SECRET"):
        _release_settings(customer_token_secret="short")


def test_release_rejects_enabled_ai_without_key():
    with pytest.raises(ValidationError, match="AI_API_KEY"):
        _release_settings(ai_provider="openai", ai_api_key="change-me")


def test_release_rejects_incomplete_paypal():
    with pytest.raises(ValidationError, match="PAYPAL"):
        _release_settings(paypal_mode="sandbox")


def test_release_rejects_non_https_paypal_urls():
    with pytest.raises(ValidationError, match="https"):
        _release_settings(
            paypal_mode="sandbox",
            paypal_client_id="client",
            paypal_client_secret="secret",
            paypal_return_url="http://example.org/return",
            paypal_cancel_url="http://example.org/cancel",
        )


def test_release_rejects_live_payments_by_default():
    with pytest.raises(ValidationError, match="live"):
        _release_settings(
            paypal_mode="live",
            paypal_client_id="client",
            paypal_client_secret="secret",
            paypal_return_url="https://example.org/return",
            paypal_cancel_url="https://example.org/cancel",
        )


def test_release_accepts_complete_sandbox_configuration():
    settings = _release_settings(
        paypal_mode="sandbox",
        paypal_client_id="client",
        paypal_client_secret="secret",
        paypal_return_url="https://example.org/#/return",
        paypal_cancel_url="https://example.org/#/cancel",
    )
    assert settings.is_release
    assert settings.paypal_api_base == "https://api.sandbox.paypal.com"
