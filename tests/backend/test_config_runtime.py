# -*- coding: utf-8 -*-
import importlib

import pytest


@pytest.mark.unit
def test_validate_runtime_settings_flags_demo_mode_in_production(monkeypatch):
    import backend.config as config

    with monkeypatch.context() as patch:
        patch.setenv('ENVIRONMENT', 'production')
        patch.setenv('STRICT_PRODUCTION_MODE', 'true')
        patch.setenv('PUBLIC_DEMO_MODE', 'true')
        patch.setenv('SESSION_BACKEND', 'file')
        patch.setenv('SECRET_KEY', 'x' * 32)

        config = importlib.reload(config)
        issues = config.validate_runtime_settings()

        assert any('PUBLIC_DEMO_MODE' in issue for issue in issues)
        assert any('SESSION_BACKEND=file' in issue for issue in issues)

    importlib.reload(config)


@pytest.mark.unit
def test_validate_runtime_settings_accepts_production_baseline(monkeypatch):
    import backend.config as config

    with monkeypatch.context() as patch:
        patch.setenv('ENVIRONMENT', 'production')
        patch.setenv('STRICT_PRODUCTION_MODE', 'true')
        patch.setenv('PUBLIC_DEMO_MODE', 'false')
        patch.setenv('SESSION_BACKEND', 'redis')
        patch.setenv('MONGODB_URL', 'mongodb://mongo:27017')
        patch.setenv('REDIS_URL', 'redis://redis:6379/0')
        patch.setenv('SECRET_KEY', 'x' * 32)

        config = importlib.reload(config)
        issues = config.validate_runtime_settings()

        assert issues == []

    importlib.reload(config)
