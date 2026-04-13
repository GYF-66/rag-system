# -*- coding: utf-8 -*-
"""Session backends for demo and production profiles."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    ENVIRONMENT,
    MAX_HISTORY_TURNS,
    MEMORY_DIR,
    MONGODB_REQUIRED,
    MONGODB_URL,
    REDIS_SESSION_TTL,
    REDIS_URL,
    SESSIONS_DIR,
    SESSION_BACKEND,
    STRICT_PRODUCTION_MODE,
)

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover - optional dependency
    redis_async = None


class MongoSessionManager:
    """MongoDB-backed session manager."""

    def __init__(self):
        self._repo = None

    def _get_repo(self):
        if self._repo is None:
            from database import SessionRepository

            self._repo = SessionRepository()
        return self._repo

    async def create_session(self, user_id: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        repo = self._get_repo()
        await repo.create_session(session_id, user_id)
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        repo = self._get_repo()
        session = await repo.get_session(session_id)
        if session:
            session.pop('_id', None)
        return session

    async def update_session(self, session_id: str, user_message: str, assistant_message: str) -> bool:
        repo = self._get_repo()
        collection = await repo._get_collection()

        now = datetime.now()
        result = await collection.update_one(
            {'session_id': session_id},
            {
                '$push': {
                    'messages': {
                        '$each': [
                            {'role': 'user', 'content': user_message, 'timestamp': now.isoformat()},
                            {'role': 'assistant', 'content': assistant_message, 'timestamp': now.isoformat()},
                        ]
                    }
                },
                '$set': {'updated_at': now},
            },
        )

        if result.modified_count > 0:
            max_msgs = MAX_HISTORY_TURNS * 2
            session = await self.get_session(session_id)
            if session and len(session.get('messages', [])) > max_msgs:
                await collection.update_one(
                    {'session_id': session_id},
                    {'$set': {'messages': session['messages'][-max_msgs:]}},
                )
            return True
        return False

    async def get_session_history(self, session_id: str) -> List[Dict]:
        session = await self.get_session(session_id)
        if not session:
            return []
        return session.get('messages', [])

    async def delete_session(self, session_id: str) -> bool:
        repo = self._get_repo()
        return await repo.delete_one({'session_id': session_id})

    async def list_user_sessions(self, user_id: str) -> List[Dict]:
        repo = self._get_repo()
        sessions = await repo.find_many(
            {'user_id': user_id},
            projection={'_id': 0, 'session_id': 1, 'created_at': 1, 'updated_at': 1, 'messages': 1},
            sort=[('updated_at', -1)],
        )
        return [
            {
                'session_id': session['session_id'],
                'created_at': _serialize_timestamp(session.get('created_at')),
                'updated_at': _serialize_timestamp(session.get('updated_at')),
                'message_count': len(session.get('messages', [])),
            }
            for session in sessions
        ]


class RedisSessionManager:
    """Redis-backed async session manager."""

    SESSION_PREFIX = 'session:'
    USER_SESSIONS_PREFIX = 'user_sessions:'

    def __init__(self, redis_url: str = REDIS_URL, ttl_seconds: int = REDIS_SESSION_TTL):
        if redis_async is None:
            raise RuntimeError('redis is not installed')
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.redis_client = redis_async.from_url(redis_url, decode_responses=True)

    async def ping(self) -> None:
        await self.redis_client.ping()

    async def close(self) -> None:
        await self.redis_client.aclose()

    async def create_session(self, user_id: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': [],
        }
        await self.redis_client.setex(
            f'{self.SESSION_PREFIX}{session_id}',
            self.ttl_seconds,
            json.dumps(session_data, ensure_ascii=False),
        )
        if user_id:
            user_key = f'{self.USER_SESSIONS_PREFIX}{user_id}'
            await self.redis_client.sadd(user_key, session_id)
            await self.redis_client.expire(user_key, self.ttl_seconds)
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        data = await self.redis_client.get(f'{self.SESSION_PREFIX}{session_id}')
        if not data:
            return None
        return json.loads(data)

    async def update_session(self, session_id: str, user_message: str, assistant_message: str) -> bool:
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        now = datetime.now().isoformat()
        session_data['messages'].extend(
            [
                {'role': 'user', 'content': user_message, 'timestamp': now},
                {'role': 'assistant', 'content': assistant_message, 'timestamp': now},
            ]
        )
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(session_data['messages']) > max_msgs:
            session_data['messages'] = session_data['messages'][-max_msgs:]
        session_data['updated_at'] = now

        await self.redis_client.setex(
            f'{self.SESSION_PREFIX}{session_id}',
            self.ttl_seconds,
            json.dumps(session_data, ensure_ascii=False),
        )
        return True

    async def get_session_history(self, session_id: str) -> List[Dict]:
        session_data = await self.get_session(session_id)
        if not session_data:
            return []
        return session_data.get('messages', [])

    async def delete_session(self, session_id: str) -> bool:
        deleted = await self.redis_client.delete(f'{self.SESSION_PREFIX}{session_id}')
        return bool(deleted)

    async def list_user_sessions(self, user_id: str) -> List[Dict]:
        user_key = f'{self.USER_SESSIONS_PREFIX}{user_id}'
        session_ids = await self.redis_client.smembers(user_key)
        sessions = []
        for sid in session_ids:
            session_data = await self.get_session(sid)
            if session_data:
                sessions.append(
                    {
                        'session_id': session_data['session_id'],
                        'created_at': session_data['created_at'],
                        'updated_at': session_data['updated_at'],
                        'message_count': len(session_data.get('messages', [])),
                    }
                )
        sessions.sort(key=lambda item: item['updated_at'], reverse=True)
        return sessions


class FileSessionManager:
    """Filesystem-backed session manager for local demo mode."""

    def __init__(self):
        self.sessions_dir = SESSIONS_DIR

    async def create_session(self, user_id: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': [],
        }
        self._save_session(session_id, session_data)
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        session_file = self.sessions_dir / f'{session_id}.json'
        if not session_file.exists():
            return None
        try:
            with open(session_file, 'r', encoding='utf-8') as file_obj:
                return json.load(file_obj)
        except Exception as exc:
            logger.error('Failed to read session %s: %s', session_id, exc)
            return None

    async def update_session(self, session_id: str, user_message: str, assistant_message: str) -> bool:
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        now = datetime.now().isoformat()
        session_data['messages'].extend(
            [
                {'role': 'user', 'content': user_message, 'timestamp': now},
                {'role': 'assistant', 'content': assistant_message, 'timestamp': now},
            ]
        )

        if len(session_data['messages']) > MAX_HISTORY_TURNS * 2:
            session_data['messages'] = session_data['messages'][-MAX_HISTORY_TURNS * 2 :]

        session_data['updated_at'] = now
        self._save_session(session_id, session_data)
        return True

    async def get_session_history(self, session_id: str) -> List[Dict]:
        session_data = await self.get_session(session_id)
        if not session_data:
            return []
        return session_data.get('messages', [])

    async def delete_session(self, session_id: str) -> bool:
        session_file = self.sessions_dir / f'{session_id}.json'
        if not session_file.exists():
            return False
        try:
            session_file.unlink()
            return True
        except Exception as exc:
            logger.error('Failed to delete session %s: %s', session_id, exc)
            return False

    async def list_user_sessions(self, user_id: str) -> List[Dict]:
        sessions = []
        for session_file in self.sessions_dir.glob('*.json'):
            try:
                with open(session_file, 'r', encoding='utf-8') as file_obj:
                    session_data = json.load(file_obj)
                if session_data.get('user_id') == user_id:
                    sessions.append(
                        {
                            'session_id': session_data['session_id'],
                            'created_at': session_data['created_at'],
                            'updated_at': session_data['updated_at'],
                            'message_count': len(session_data.get('messages', [])),
                        }
                    )
            except Exception as exc:
                logger.error('Failed to scan session file %s: %s', session_file, exc)
        sessions.sort(key=lambda item: item['updated_at'], reverse=True)
        return sessions

    def _save_session(self, session_id: str, session_data: Dict):
        session_file = self.sessions_dir / f'{session_id}.json'
        with open(session_file, 'w', encoding='utf-8') as file_obj:
            json.dump(session_data, file_obj, ensure_ascii=False, indent=2)


class MemoryManager:
    """Simple file-backed user memory store."""

    def __init__(self):
        self.memory_dir = MEMORY_DIR

    def save_learned_knowledge(self, user_id: str, topic: str, knowledge: str):
        memory_file = self.memory_dir / f'{user_id}.json'
        memory_data = {}
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as file_obj:
                memory_data = json.load(file_obj)
        if 'learned_knowledge' not in memory_data:
            memory_data['learned_knowledge'] = {}
        memory_data['learned_knowledge'][topic] = {
            'content': knowledge,
            'learned_at': datetime.now().isoformat(),
        }
        with open(memory_file, 'w', encoding='utf-8') as file_obj:
            json.dump(memory_data, file_obj, ensure_ascii=False, indent=2)

    def get_user_memory(self, user_id: str) -> Dict:
        memory_file = self.memory_dir / f'{user_id}.json'
        if not memory_file.exists():
            return {}
        with open(memory_file, 'r', encoding='utf-8') as file_obj:
            return json.load(file_obj)


def _serialize_timestamp(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or '')


async def close_session_manager(manager) -> None:
    close = getattr(manager, 'close', None)
    if close is None:
        return
    result = close()
    if hasattr(result, '__await__'):
        await result


def _can_use_mongo_sessions() -> bool:
    if not MONGODB_URL:
        return False

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        async def _ping() -> bool:
            client = AsyncIOMotorClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=1500,
                connectTimeoutMS=1500,
                socketTimeoutMS=1500,
            )
            try:
                await client.admin.command('ping')
                return True
            finally:
                client.close()

        loop = None
        try:
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(_ping())
        finally:
            if loop is not None:
                loop.close()
    except Exception as exc:
        logger.warning('MongoDB session backend unavailable: %s', exc)
        return False


def _create_session_manager():
    backend = SESSION_BACKEND or 'auto'

    if backend == 'redis':
        return RedisSessionManager()

    if backend == 'mongo':
        if not MONGODB_URL:
            raise RuntimeError('SESSION_BACKEND=mongo requires MONGODB_URL')
        return MongoSessionManager()

    if backend == 'file':
        if STRICT_PRODUCTION_MODE and ENVIRONMENT == 'production':
            raise RuntimeError('SESSION_BACKEND=file is not allowed in strict production mode')
        return FileSessionManager()

    if backend == 'auto':
        if redis_async is not None:
            try:
                mgr = RedisSessionManager()
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(mgr.ping())
                finally:
                    loop.close()
                logger.info('Using Redis session backend')
                return mgr
            except Exception as exc:
                logger.warning('Redis session backend unavailable: %s', exc)
        if MONGODB_URL:
            if MONGODB_REQUIRED or _can_use_mongo_sessions():
                logger.info('Using MongoDB session backend')
                return MongoSessionManager()
            logger.warning('MongoDB session backend unavailable, falling back to file sessions')
        if STRICT_PRODUCTION_MODE and ENVIRONMENT == 'production':
            raise RuntimeError('No production-ready session backend is available; configure Redis or MongoDB')
        logger.info('Falling back to file session backend')
        return FileSessionManager()

    raise RuntimeError(f'Unsupported SESSION_BACKEND: {backend}')


session_manager = _create_session_manager()
memory_manager = MemoryManager()

