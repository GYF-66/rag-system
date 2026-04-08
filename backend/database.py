# -*- coding: utf-8 -*-
"""MongoDB helpers and repositories used by the FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    COLLECTION_SESSIONS,
    COLLECTION_SPACES,
    COLLECTION_TOKENS,
    COLLECTION_USERS,
    MONGODB_DATABASE,
    MONGODB_MAX_IDLE_TIME,
    MONGODB_MAX_POOL_SIZE,
    MONGODB_MIN_POOL_SIZE,
    MONGODB_SERVER_SELECTION_TIMEOUT,
    MONGODB_URL,
)

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_database = None

CONNECTION_POOL_CONFIG = {
    'maxPoolSize': MONGODB_MAX_POOL_SIZE,
    'minPoolSize': MONGODB_MIN_POOL_SIZE,
    'maxIdleTimeMS': MONGODB_MAX_IDLE_TIME,
    'serverSelectionTimeoutMS': MONGODB_SERVER_SELECTION_TIMEOUT,
    'connectTimeoutMS': 10000,
    'socketTimeoutMS': 30000,
    'retryWrites': True,
    'retryReads': True,
    'w': 'majority',
}


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        if not MONGODB_URL:
            raise RuntimeError('MongoDB is not configured')
        _client = AsyncIOMotorClient(MONGODB_URL, **CONNECTION_POOL_CONFIG)
        logger.info('MongoDB client created for %s', MONGODB_URL)
    return _client


async def get_database():
    global _database
    if _database is None:
        client = get_client()
        _database = client[MONGODB_DATABASE]
        logger.info('MongoDB database initialized: %s', MONGODB_DATABASE)
    return _database


@asynccontextmanager
async def get_collection(collection_name: str):
    db = await get_database()
    yield db[collection_name]


async def check_connection() -> Dict[str, Any]:
    if not MONGODB_URL:
        return {
            'status': 'disabled',
            'timestamp': datetime.now().isoformat(),
            'error': 'MongoDB is not configured',
        }

    try:
        client = get_client()
        await client.admin.command('ping')
        server_info = await client.admin.command('serverStatus')
        db = await get_database()
        stats = await db.command('dbStats')
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'server_version': server_info.get('version'),
            'uptime': server_info.get('uptime'),
            'connections': server_info.get('connections', {}),
            'database_stats': {
                'collections': stats.get('collections'),
                'data_size': stats.get('dataSize'),
                'storage_size': stats.get('storageSize'),
            },
        }
    except Exception as exc:
        logger.error('Database health check failed: %s', exc)
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(exc),
        }


async def close_database() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info('MongoDB connection closed')


class MongoDBRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    async def _get_collection(self):
        db = await get_database()
        return db[self.collection_name]

    async def insert_one(self, document: Dict[str, Any]) -> str:
        collection = await self._get_collection()
        result = await collection.insert_one(document)
        return str(result.inserted_id)

    async def find_one(
        self,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        collection = await self._get_collection()
        return await collection.find_one(filter_dict, projection)

    async def find_many(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[list] = None,
    ) -> list:
        collection = await self._get_collection()
        cursor = collection.find(filter_dict or {}, projection)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=limit)

    async def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> bool:
        collection = await self._get_collection()
        result = await collection.update_one(filter_dict, {'$set': update_dict})
        return result.modified_count > 0

    async def delete_one(self, filter_dict: Dict[str, Any]) -> bool:
        collection = await self._get_collection()
        result = await collection.delete_one(filter_dict)
        return result.deleted_count > 0

    async def count_documents(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        collection = await self._get_collection()
        return await collection.count_documents(filter_dict or {})


class UserRepository(MongoDBRepository):
    def __init__(self):
        super().__init__(COLLECTION_USERS)

    async def create_user(self, user_id: str, openid: str, nickname: str = None, avatar: str = None) -> str:
        document = {
            'user_id': user_id,
            'openid': openid,
            'nickname': nickname,
            'avatar': avatar,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_active': True,
        }
        return await self.insert_one(document)

    async def get_user_by_openid(self, openid: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({'openid': openid})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({'user_id': user_id})


class SessionRepository(MongoDBRepository):
    def __init__(self):
        super().__init__(COLLECTION_SESSIONS)

    async def create_session(self, session_id: str, user_id: str = None) -> str:
        document = {
            'session_id': session_id,
            'user_id': user_id,
            'messages': [],
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        return await self.insert_one(document)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({'session_id': session_id})

    async def add_message(self, session_id: str, role: str, content: str) -> bool:
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(),
        }
        collection = await self._get_collection()
        result = await collection.update_one(
            {'session_id': session_id},
            {
                '$push': {'messages': message},
                '$set': {'updated_at': datetime.now()},
            },
        )
        return result.modified_count > 0


class TokenRepository(MongoDBRepository):
    def __init__(self):
        super().__init__(COLLECTION_TOKENS)

    async def save_token(
        self,
        user_id: str,
        token: str,
        expires_at: datetime,
        device_type: str = 'web',
    ) -> str:
        document = {
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at,
            'device_type': device_type,
            'created_at': datetime.now(),
            'is_revoked': False,
        }
        return await self.insert_one(document)

    async def get_token(self, token: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({'token': token, 'is_revoked': False})

    async def revoke_token(self, token: str) -> bool:
        return await self.update_one({'token': token}, {'is_revoked': True, 'revoked_at': datetime.now()})

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        collection = await self._get_collection()
        result = await collection.update_many(
            {'user_id': user_id, 'is_revoked': False},
            {'$set': {'is_revoked': True, 'revoked_at': datetime.now()}},
        )
        return result.modified_count


class SpaceRepository(MongoDBRepository):
    def __init__(self):
        super().__init__(COLLECTION_SPACES)

    async def create_space(
        self,
        space_id: str,
        name: str,
        description: str = None,
        icon: str = None,
        color: str = None,
    ) -> str:
        document = {
            'id': space_id,
            'name': name,
            'description': description,
            'icon': icon,
            'color': color,
            'item_count': 0,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        return await self.insert_one(document)

    async def get_space(self, space_id: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({'id': space_id})

    async def list_spaces(self, user_id: str = None) -> list:
        filter_dict = {'user_id': user_id} if user_id else {}
        return await self.find_many(filter_dict, sort=[('updated_at', -1)])


user_repository = UserRepository()
session_repository = SessionRepository()
token_repository = TokenRepository()
space_repository = SpaceRepository()
