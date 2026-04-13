# -*- coding: utf-8 -*-
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import session_manager as session_manager_module


def test_auto_session_backend_falls_back_to_file_when_mongo_unavailable(monkeypatch):
    monkeypatch.setattr(session_manager_module, 'SESSION_BACKEND', 'auto')
    monkeypatch.setattr(session_manager_module, 'redis_async', None)
    monkeypatch.setattr(session_manager_module, 'MONGODB_URL', 'mongodb://localhost:27017')
    monkeypatch.setattr(session_manager_module, 'MONGODB_REQUIRED', False)
    monkeypatch.setattr(session_manager_module, 'STRICT_PRODUCTION_MODE', False)
    monkeypatch.setattr(session_manager_module, 'ENVIRONMENT', 'development')
    monkeypatch.setattr(session_manager_module, '_can_use_mongo_sessions', lambda: False)

    manager = session_manager_module._create_session_manager()

    assert isinstance(manager, session_manager_module.FileSessionManager)
