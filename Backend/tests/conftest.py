"""Mantiene las pruebas independientes de las credenciales locales y del VPS."""

import os

import pytest


def _clear_settings_environment(monkeypatch):
    for name in list(os.environ):
        if name.upper().startswith("TALLERCLARO_") or name.upper() == "DATABASE_URL":
            monkeypatch.delenv(name)


def _disable_dotenv(monkeypatch):
    """Impide que las pruebas lean Backend/.env, que ahora se resuelve por ruta absoluta."""
    from tallerclaro.bootstrap.settings import Settings

    monkeypatch.setitem(Settings.model_config, "env_file", None)


@pytest.fixture(autouse=True)
def isolated_settings_environment(monkeypatch, tmp_path):
    # Importar main.py dentro de los tests/fixtures, después de este aislamiento.
    monkeypatch.chdir(tmp_path)
    _clear_settings_environment(monkeypatch)
    _disable_dotenv(monkeypatch)
