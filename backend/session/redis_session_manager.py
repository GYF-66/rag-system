# -*- coding: utf-8 -*-
"""
Redis 会话管理器
替代文件系统存储，提供更高性能的会话管理
当 Redis 不可用时自动降级到文件系统存储
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional

from config import MAX_HISTORY_TURNS

logger = logging.getLogger(__name__)

# 尝试导入 Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisSessionManager:
    """基于 Redis 的会话管理器"""

    SESSION_TTL = 86400  # 24小时过期
    SESSION_PREFIX = "session:"
    USER_SESSIONS_PREFIX = "user_sessions:"

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    redis_url, decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Redis 会话管理器初始化成功")
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis 连接失败，将降级到文件存储: {e}")
                self.redis_client = None
        else:
            logger.warning("redis 包未安装，将降级到文件存储")

    @property
    def is_available(self) -> bool:
        return self.redis_client is not None

    def create_session(self, user_id: Optional[str] = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': []
        }

        key = f"{self.SESSION_PREFIX}{session_id}"
        self.redis_client.setex(key, self.SESSION_TTL, json.dumps(session_data, ensure_ascii=False))

        # 维护用户会话索引
        if user_id:
            user_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
            self.redis_client.sadd(user_key, session_id)
            self.redis_client.expire(user_key, self.SESSION_TTL)

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        key = f"{self.SESSION_PREFIX}{session_id}"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    def update_session(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str
    ) -> bool:
        """更新会话，添加新消息"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        session_data['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        session_data['messages'].append({
            'role': 'assistant',
            'content': assistant_message,
            'timestamp': datetime.now().isoformat()
        })

        # 限制历史记录长度
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(session_data['messages']) > max_msgs:
            session_data['messages'] = session_data['messages'][-max_msgs:]

        session_data['updated_at'] = datetime.now().isoformat()

        key = f"{self.SESSION_PREFIX}{session_id}"
        self.redis_client.setex(key, self.SESSION_TTL, json.dumps(session_data, ensure_ascii=False))
        return True

    def get_session_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        session_data = self.get_session(session_id)
        if not session_data:
            return []
        return session_data.get('messages', [])

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        key = f"{self.SESSION_PREFIX}{session_id}"
        return bool(self.redis_client.delete(key))

    def list_user_sessions(self, user_id: str) -> List[Dict]:
        """列出用户的所有会话（O(1) 查找，无需遍历文件）"""
        user_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        session_ids = self.redis_client.smembers(user_key)

        sessions = []
        for sid in session_ids:
            session_data = self.get_session(sid)
            if session_data:
                sessions.append({
                    'session_id': session_data['session_id'],
                    'created_at': session_data['created_at'],
                    'updated_at': session_data['updated_at'],
                    'message_count': len(session_data.get('messages', []))
                })

        sessions.sort(key=lambda x: x['updated_at'], reverse=True)
        return sessions


def get_session_manager():
    """
    获取最佳可用的会话管理器
    优先使用 Redis，不可用时降级到文件系统
    """
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    if REDIS_AVAILABLE:
        redis_mgr = RedisSessionManager(redis_url)
        if redis_mgr.is_available:
            return redis_mgr

    # 降级到文件系统
    from session_manager import session_manager
    logger.info("使用文件系统会话管理器")
    return session_manager
