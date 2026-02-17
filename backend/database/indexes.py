# -*- coding: utf-8 -*-
"""
MongoDB 索引管理模块

功能：
- 创建数据库索引
- 验证索引状态
- 删除索引
"""
import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient
from config import (
    MONGODB_URL,
    MONGODB_DATABASE,
    COLLECTION_USERS,
    COLLECTION_SESSIONS,
    COLLECTION_TOKENS,
    COLLECTION_SPACES
)

logger = logging.getLogger(__name__)


async def create_indexes():
    """
    创建数据库索引

    为所有集合创建必要的索引以提升查询性能
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]

    try:
        # users 集合索引
        logger.info("创建 users 集合索引...")
        await db.users.create_index([('openid', 1)], unique=True, name='openid_unique')
        await db.users.create_index([('user_id', 1)], unique=True, name='user_id_unique')
        await db.users.create_index([('created_at', -1)], name='created_at_idx')
        logger.info("✓ users 集合索引创建完成")

        # sessions 集合索引
        logger.info("创建 sessions 集合索引...")
        await db.sessions.create_index([('session_id', 1)], unique=True, name='session_id_unique')
        await db.sessions.create_index([('user_id', 1)], name='user_id_idx')
        await db.sessions.create_index([('user_id', 1), ('updated_at', -1)], name='user_id_updated_at_idx')
        logger.info("✓ sessions 集合索引创建完成")

        # tokens 集合索引
        logger.info("创建 tokens 集合索引...")
        await db.tokens.create_index([('token', 1)], unique=True, name='token_unique')
        await db.tokens.create_index([('user_id', 1)], name='user_id_idx')
        await db.tokens.create_index([('expires_at', 1)], name='expires_at_idx')
        await db.tokens.create_index([('user_id', 1), ('is_revoked', 1)], name='user_id_is_revoked_idx')
        logger.info("✓ tokens 集合索引创建完成")

        # spaces 集合索引
        logger.info("创建 spaces 集合索引...")
        await db.spaces.create_index([('id', 1)], unique=True, name='id_unique')
        await db.spaces.create_index([('user_id', 1)], name='user_id_idx')
        logger.info("✓ spaces 集合索引创建完成")

        logger.info("=" * 60)
        logger.info("✓ MongoDB 所有索引创建完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"创建索引失败: {e}")
        raise
    finally:
        client.close()


async def list_indexes(collection_name: str):
    """
    列出集合的所有索引

    Args:
        collection_name: 集合名称
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]

    try:
        collection = db[collection_name]
        indexes = await collection.list_indexes()

        logger.info(f"\n{collection_name} 集合索引列表:")
        logger.info("-" * 60)
        for idx in indexes:
            logger.info(f"  名称: {idx.get('name')}")
            logger.info(f"  键: {idx.get('key')}")
            logger.info(f"  唯一: {idx.get('unique', False)}")
            logger.info("-" * 60)

    except Exception as e:
        logger.error(f"列出索引失败: {e}")
    finally:
        client.close()


async def drop_index(collection_name: str, index_name: str):
    """
    删除指定索引

    Args:
        collection_name: 集合名称
        index_name: 索引名称
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]

    try:
        collection = db[collection_name]
        await collection.drop_index(index_name)
        logger.info(f"✓ 已删除索引: {collection_name}.{index_name}")
    except Exception as e:
        logger.error(f"删除索引失败: {e}")
    finally:
        client.close()


async def verify_indexes():
    """
    验证所有索引是否存在

    Returns:
        bool: 所有索引是否存在
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]

    expected_indexes = {
        COLLECTION_USERS: ['openid_unique', 'user_id_unique', 'created_at_idx'],
        COLLECTION_SESSIONS: ['session_id_unique', 'user_id_idx', 'user_id_updated_at_idx'],
        COLLECTION_TOKENS: ['token_unique', 'user_id_idx', 'expires_at_idx', 'user_id_is_revoked_idx'],
        COLLECTION_SPACES: ['id_unique', 'user_id_idx']
    }

    all_verified = True

    try:
        for collection_name, expected_names in expected_indexes.items():
            collection = db[collection_name]
            indexes = await collection.list_indexes()
            existing_names = {idx.get('name') for idx in indexes}

            for expected_name in expected_names:
                if expected_name in existing_names:
                    logger.info(f"✓ {collection_name}.{expected_name} 索引存在")
                else:
                    logger.warning(f"✗ {collection_name}.{expected_name} 索引不存在")
                    all_verified = False

        return all_verified

    except Exception as e:
        logger.error(f"验证索引失败: {e}")
        return False
    finally:
        client.close()


async def recreate_all_indexes():
    """
    重新创建所有索引

    注意：此操作会删除所有现有索引并重新创建
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]

    try:
        # 获取所有集合
        collections = [COLLECTION_USERS, COLLECTION_SESSIONS, COLLECTION_TOKENS, COLLECTION_SPACES]

        for collection_name in collections:
            collection = db[collection_name]
            indexes = await collection.list_indexes()

            # 删除所有索引（除了 _id）
            for idx in indexes:
                index_name = idx.get('name')
                if index_name != '_id_':
                    try:
                        await collection.drop_index(index_name)
                        logger.info(f"✓ 已删除索引: {collection_name}.{index_name}")
                    except Exception as e:
                        logger.warning(f"删除索引失败: {collection_name}.{index_name}: {e}")

        # 重新创建所有索引
        await create_indexes()

    except Exception as e:
        logger.error(f"重新创建索引失败: {e}")
        raise
    finally:
        client.close()


if __name__ == '__main__':
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 解析命令行参数
    command = sys.argv[1] if len(sys.argv) > 1 else 'create'

    if command == 'create':
        asyncio.run(create_indexes())
    elif command == 'list':
        # 列出所有集合的索引
        collections = [COLLECTION_USERS, COLLECTION_SESSIONS, COLLECTION_TOKENS, COLLECTION_SPACES]
        for coll in collections:
            asyncio.run(list_indexes(coll))
    elif command == 'verify':
        result = asyncio.run(verify_indexes())
        if result:
            logger.info("\n✓ 所有索引验证通过")
        else:
            logger.warning("\n✗ 部分索引缺失，请运行 'create' 命令")
    elif command == 'recreate':
        asyncio.run(recreate_all_indexes())
    else:
        print("使用方法:")
        print("  python indexes.py create   # 创建索引")
        print("  python indexes.py list     # 列出索引")
        print("  python indexes.py verify  # 验证索引")
        print("  python indexes.py recreate # 重新创建索引")