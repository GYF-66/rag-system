# -*- coding: utf-8 -*-
"""
认证授权模块 - Web 端版本
支持用户名密码登录和 JWT Token 鉴权
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from database import user_repository, token_repository

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    哈希密码

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌

    Args:
        data: Token 载荷数据
        expires_delta: 过期时间增量

    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'access'
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建刷新令牌

    Args:
        data: Token 载荷数据
        expires_delta: 过期时间增量

    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'refresh'
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 Token

    Args:
        token: JWT Token 字符串

    Returns:
        解码后的数据，失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token 无效: {e}")
        return None


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    验证 Token 依赖

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        Token 载荷数据

    Raises:
        HTTPException: Token 无效或过期
    """
    token = credentials.credentials

    # 解码 Token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查 Token 是否被撤销
    token_data = await token_repository.get_token(token)
    if not token_data or token_data.get('is_revoked'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已被撤销",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    token_payload: Dict[str, Any] = Depends(verify_token)
) -> Dict[str, Any]:
    """
    获取当前用户

    Args:
        token_payload: Token 载荷数据

    Returns:
        用户信息

    Raises:
        HTTPException: 用户不存在
    """
    user_id = token_payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户信息"
        )

    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    return user


class AuthService:
    """认证服务"""

    async def register(
        self,
        username: str,
        password: str,
        nickname: str = None,
        avatar: str = None
    ) -> Dict[str, Any]:
        """
        用户注册

        Args:
            username: 用户名
            password: 密码
            nickname: 昵称
            avatar: 头像

        Returns:
            注册响应，包含 Token 和用户信息
        """
        # 检查用户名是否已存在
        existing_user = await user_repository.find_one({'username': username})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )

        # 创建新用户
        import uuid
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)

        await user_repository.insert_one({
            'user_id': user_id,
            'username': username,
            'password': hashed_password,
            'nickname': nickname or username,
            'avatar': avatar,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_active': True
        })

        # 生成 Token
        access_token = create_access_token(
            data={'sub': user_id, 'username': username}
        )
        refresh_token = create_refresh_token(
            data={'sub': user_id, 'username': username}
        )

        # 保存 Token 到数据库
        access_expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        await token_repository.save_token(
            user_id=user_id,
            token=access_token,
            expires_at=access_expires_at,
            device_type='web'
        )
        await token_repository.save_token(
            user_id=user_id,
            token=refresh_token,
            expires_at=refresh_expires_at,
            device_type='web'
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            'user': {
                'user_id': user_id,
                'username': username,
                'nickname': nickname or username,
                'avatar': avatar
            }
        }

    async def login(
        self,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            登录响应，包含 Token 和用户信息
        """
        # 查找用户
        user = await user_repository.find_one({'username': username})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        # 验证密码
        if not verify_password(password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        # 检查用户是否激活
        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        # 生成 Token
        access_token = create_access_token(
            data={'sub': user['user_id'], 'username': username}
        )
        refresh_token = create_refresh_token(
            data={'sub': user['user_id'], 'username': username}
        )

        # 保存 Token 到数据库
        access_expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        await token_repository.save_token(
            user_id=user['user_id'],
            token=access_token,
            expires_at=access_expires_at,
            device_type='web'
        )
        await token_repository.save_token(
            user_id=user['user_id'],
            token=refresh_token,
            expires_at=refresh_expires_at,
            device_type='web'
        )

        # 更新最后登录时间
        await user_repository.update_one(
            {'user_id': user['user_id']},
            {'last_login': datetime.utcnow()}
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            'user': {
                'user_id': user['user_id'],
                'username': user['username'],
                'nickname': user.get('nickname'),
                'avatar': user.get('avatar')
            }
        }

    async def refresh_token(
        self,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        刷新 Token

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的 Token
        """
        payload = decode_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )

        user_id = payload.get('sub')
        user = await user_repository.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        # 检查用户是否激活
        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        # 生成新的访问令牌
        new_access_token = create_access_token(
            data={'sub': user_id, 'username': user['username']}
        )

        return {
            'access_token': new_access_token,
            'token_type': 'bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    async def logout(
        self,
        token: str
    ) -> bool:
        """
        登出（撤销 Token）

        Args:
            token: 要撤销的 Token

        Returns:
            是否成功
        """
        return await token_repository.revoke_token(token)

    async def logout_all(
        self,
        user_id: str
    ) -> int:
        """
        登出所有设备（撤销用户所有 Token）

        Args:
            user_id: 用户 ID

        Returns:
            撤销的 Token 数量
        """
        return await token_repository.revoke_all_user_tokens(user_id)

    async def update_profile(
        self,
        user_id: str,
        nickname: str = None,
        avatar: str = None
    ) -> bool:
        """
        更新用户资料

        Args:
            user_id: 用户 ID
            nickname: 昵称
            avatar: 头像

        Returns:
            是否成功
        """
        update_data = {'updated_at': datetime.now()}
        if nickname:
            update_data['nickname'] = nickname
        if avatar:
            update_data['avatar'] = avatar

        return await user_repository.update_one(
            {'user_id': user_id},
            update_data
        )

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        修改密码

        Args:
            user_id: 用户 ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            是否成功
        """
        user = await user_repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 验证旧密码
        if not verify_password(old_password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码错误"
            )

        # 更新密码
        hashed_password = hash_password(new_password)
        return await user_repository.update_one(
            {'user_id': user_id},
            {'password': hashed_password, 'updated_at': datetime.now()}
        )


# 全局实例
auth_service = AuthService()