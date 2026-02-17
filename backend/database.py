# -*- coding: utf-8 -*-
"""
数据库配置 - MongoDB 连接模块

特性：
- 连接池管理
- 自动重连机制
- 健康检查
- 环境配置支持
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from config import (
    MONGODB_URL,
    MONGODB_DATABASE,
    MONGODB_MAX_POOL_SIZE,
    MONGODB_MIN_POOL_SIZE,
    MONGODB_MAX_IDLE_TIME,
    MONGODB_SERVER_SELECTION_TIMEOUT,
    COLLECTION_USERS,
    COLLECTION_SESSIONS,
    COLLECTION_TOKENS,
    COLLECTION_SPACES
)

logger = logging.getLogger(__name__)

# 全局客户端实例
_client: Optional[AsyncIOMotorClient] = None
_database = None

# 连接池配置
CONNECTION_POOL_CONFIG = {
    'maxPoolSize': MONGODB_MAX_POOL_SIZE,      # 最大连接数
    'minPoolSize': MONGODB_MIN_POOL_SIZE,      # 最小连接数
    'maxIdleTimeMS': MONGODB_MAX_IDLE_TIME,    # 连接最大空闲时间
    'serverSelectionTimeoutMS': MONGODB_SERVER_SELECTION_TIMEOUT,  # 服务器选择超时
    'connectTimeoutMS': 10000,                 # 连接超时
    'socketTimeoutMS': 30000,                  # Socket 超时
    'retryWrites': True,                       # 自动重试写操作
    'retryReads': True,                        # 自动重试读操作
    'w': 'majority',                           # 写确认级别
}


def get_client() -> AsyncIOMotorClient:
    """
    获取 MongoDB 客户端实例（单例模式）

    Returns:
        AsyncIOMotorClient: MongoDB 客户端
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGODB_URL,
            **CONNECTION_POOL_CONFIG
        )
        logger.info(f"MongoDB 客户端已创建: {MONGODB_URL}")
    return _client


async def get_database():
    """
    获取数据库实例

    Returns:
        Database: MongoDB 数据库实例
    """
    global _database
    if _database is None:
        client = get_client()
        _database = client[MONGODB_DATABASE]
        logger.info(f"数据库实例已获取: {MONGODB_DATABASE}")
    return _database


@asynccontextmanager
async def get_collection(collection_name: str):
    """
    获取集合的上下文管理器

    Args:
        collection_name: 集合名称

    Yields:
        Collection: MongoDB 集合实例
    """
    db = await get_database()
    collection = db[collection_name]
    try:
        yield collection
    except Exception as e:
        logger.error(f"集合操作失败 [{collection_name}]: {e}")
        raise


async def check_connection() -> Dict[str, Any]:
    """
    检查数据库连接健康状态

    Returns:
        健康状态信息
    """
    try:
        client = get_client()
        # 发送 ping 命令
        await client.admin.command('ping')

        # 获取服务器信息
        server_info = await client.admin.command('serverStatus')

        # 获取统计信息
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
            }
        }
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }


async def close_database():
    """
    关闭数据库连接
    """
    global _client, _database

    if _client is not None:
        await _client.close()
        _client = None
        _database = None
        logger.info("MongoDB 连接已关闭")


class MongoDBRepository:
    """
    MongoDB 仓库基类
    提供通用的 CRUD 操作
    """

    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    async def _get_collection(self):
        """获取集合实例"""
        db = await get_database()
        return db[self.collection_name]

    async def insert_one(self, document: Dict[str, Any]) -> str:
        """插入单个文档"""
        collection = await self._get_collection()
        result = await collection.insert_one(document)
        return str(result.inserted_id)

    async def find_one(
        self,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """查找单个文档"""
        collection = await self._get_collection()
        return await collection.find_one(filter_dict, projection)

    async def find_many(
        self,
        filter_dict: Dict[str, Any] = None,
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[list] = None
    ) -> list:
        """查找多个文档"""
        collection = await self._get_collection()
        cursor = collection.find(filter_dict, projection)

        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        if sort:
            cursor = cursor.sort(sort)

        return await cursor.to_list(length=limit)

    async def update_one(
        self,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any]
    ) -> bool:
        """更新单个文档"""
        collection = await self._get_collection()
        result = await collection.update_one(filter_dict, {'$set': update_dict})
        return result.modified_count > 0

    async def delete_one(self, filter_dict: Dict[str, Any]) -> bool:
        """删除单个文档"""
        collection = await self._get_collection()
        result = await collection.delete_one(filter_dict)
        return result.deleted_count > 0

    async def count_documents(self, filter_dict: Dict[str, Any] = None) -> int:
        """统计文档数量"""
        collection = await self._get_collection()
        return await collection.count_documents(filter_dict or {})


class UserRepository(MongoDBRepository):
    """用户数据仓库"""

    def __init__(self):
        super().__init__(COLLECTION_USERS)

    async def create_user(
        self,
        user_id: str,
        openid: str,
        nickname: str = None,
        avatar: str = None
    ) -> str:
        """创建用户"""
        document = {
            'user_id': user_id,
            'openid': openid,
            'nickname': nickname,
            'avatar': avatar,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_active': True
        }
        return await self.insert_one(document)

    async def get_user_by_openid(self, openid: str) -> Optional[Dict]:
        """根据 openid 获取用户"""
        return await self.find_one({'openid': openid})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """根据 user_id 获取用户"""
        return await self.find_one({'user_id': user_id})


class SessionRepository(MongoDBRepository):
    """会话数据仓库"""

    def __init__(self):
        super().__init__(COLLECTION_SESSIONS)

    async def create_session(self, session_id: str, user_id: str = None) -> str:
        """创建会话"""
        document = {
            'session_id': session_id,
            'user_id': user_id,
            'messages': [],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        return await self.insert_one(document)

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话"""
        return await self.find_one({'session_id': session_id})

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """添加消息到会话"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now()
        }

        collection = await self._get_collection()
        result = await collection.update_one(
            {'session_id': session_id},
            {
                '$push': {'messages': message},
                '$set': {'updated_at': datetime.now()}
            }
        )
        return result.modified_count > 0


class TokenRepository(MongoDBRepository):
    """Token 数据仓库"""

    def __init__(self):
        super().__init__(COLLECTION_TOKENS)

    async def save_token(
        self,
        user_id: str,
        token: str,
        expires_at: datetime,
        device_type: str = 'web'
    ) -> str:
        """保存 Token"""
        document = {
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at,
            'device_type': device_type,
            'created_at': datetime.now(),
            'is_revoked': False
        }
        return await self.insert_one(document)

    async def get_token(self, token: str) -> Optional[Dict]:
        """获取 Token"""
        return await self.find_one({
            'token': token,
            'is_revoked': False
        })

    async def revoke_token(self, token: str) -> bool:
        """撤销 Token"""
        return await self.update_one(
            {'token': token},
            {'is_revoked': True, 'revoked_at': datetime.now()}
        )

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """撤销用户所有 Token"""
        collection = await self._get_collection()
        result = await collection.update_many(
            {'user_id': user_id, 'is_revoked': False},
            {'is_revoked': True, 'revoked_at': datetime.now()}
        )
        return result.modified_count


class SpaceRepository(MongoDBRepository):
    """Space 数据仓库"""

    def __init__(self):
        super().__init__(COLLECTION_SPACES)

    async def create_space(
        self,
        space_id: str,
        name: str,
        description: str = None,
        icon: str = None,
        color: str = None
    ) -> str:
        """创建 Space"""
        document = {
            'id': space_id,
            'name': name,
            'description': description,
            'icon': icon,
            'color': color,
            'item_count': 0,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        return await self.insert_one(document)

    async def get_space(self, space_id: str) -> Optional[Dict]:
        """获取 Space"""
        return await self.find_one({'id': space_id})

    async def list_spaces(self, user_id: str = None) -> list:
        """列出所有 Spaces"""
        filter_dict = {}
        if user_id:
            filter_dict['user_id'] = user_id
        return await self.find_many(filter_dict, sort=[('updated_at', -1)])


# 全局仓库实例
user_repository = UserRepository()
session_repository = SessionRepository()
token_repository = TokenRepository()
space_repository = SpaceRepository()