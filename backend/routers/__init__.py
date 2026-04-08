# -*- coding: utf-8 -*-
"""
Routers package
路由模块包
"""
from routers.spaces import router as spaces_router
from routers.auth import router as auth_router
from routers.graph import router as graph_router

__all__ = ['spaces_router', 'auth_router', 'graph_router']