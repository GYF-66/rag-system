# -*- coding: utf-8 -*-
"""Authentication service, JWT helpers and FastAPI dependencies."""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.hash import pbkdf2_sha256

from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from database import token_repository, user_repository

logger = logging.getLogger(__name__)

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

_PBKDF2_PREFIX = "$pbkdf2-sha256$"
_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='密码长度不能少于 8 位',
        )
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='密码必须包含至少一个大写字母',
        )
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='密码必须包含至少一个小写字母',
        )
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='密码必须包含至少一个数字',
        )



def hash_password(password: str) -> str:
    """Hash passwords using a backend that is stable on the current runtime."""
    return pbkdf2_sha256.hash(password)



def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False

    try:
        if hashed_password.startswith(_PBKDF2_PREFIX):
            return pbkdf2_sha256.verify(plain_password, hashed_password)

        if hashed_password.startswith(_BCRYPT_PREFIXES):
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        logger.warning('Password verification failed because the stored hash is malformed')
        return False
    except Exception:
        logger.exception('Unexpected password verification error')
        return False

    logger.warning('Unsupported password hash format encountered')
    return False



def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    expire = _utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = data.copy()
    payload.update({'exp': expire, 'iat': _utcnow(), 'type': 'access'})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    expire = _utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    payload = data.copy()
    payload.update({'exp': expire, 'iat': _utcnow(), 'type': 'refresh'})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        logger.warning('Token expired')
        return None
    except JWTError as exc:
        logger.warning('Invalid token: %s', exc)
        return None


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='无效的认证凭据',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    token_data = await token_repository.get_token(token)
    if not token_data or token_data.get('is_revoked'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token 已失效',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    return payload


async def get_current_user(token_payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    user_id = token_payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token 中缺少用户信息',
        )

    user = await user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='用户不存在',
        )

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[Dict[str, Any]]:
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get('sub')
    if not user_id:
        return None

    return await user_repository.get_user_by_id(user_id)


class AuthService:
    def _build_user_payload(self, user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'user_id': user['user_id'],
            'username': user['username'],
            'nickname': user.get('nickname'),
            'avatar': user.get('avatar'),
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at'),
            'last_login': user.get('last_login'),
        }

    async def _issue_tokens(self, user: Dict[str, Any]) -> Dict[str, Any]:
        token_data = {'sub': user['user_id'], 'username': user['username']}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        await token_repository.save_token(
            user_id=user['user_id'],
            token=access_token,
            expires_at=_utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            device_type='web',
        )
        await token_repository.save_token(
            user_id=user['user_id'],
            token=refresh_token,
            expires_at=_utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            device_type='web',
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            'user': self._build_user_payload(user),
        }

    async def register(
        self,
        username: str,
        password: str,
        nickname: str = None,
        avatar: str = None,
    ) -> Dict[str, Any]:
        existing_user = await user_repository.find_one({'username': username})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='用户名已存在',
            )

        _validate_password_strength(password)

        now = _utcnow()
        user = {
            'user_id': str(uuid.uuid4()),
            'username': username,
            'password': hash_password(password),
            'nickname': nickname or username,
            'avatar': avatar,
            'created_at': now,
            'updated_at': now,
            'is_active': True,
        }
        await user_repository.insert_one(user)
        return await self._issue_tokens(user)

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        user = await user_repository.find_one({'username': username})
        if not user or not verify_password(password, user.get('password', '')):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='用户名或密码错误',
            )

        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='用户已被禁用',
            )

        await user_repository.update_one(
            {'user_id': user['user_id']},
            {'last_login': _utcnow(), 'updated_at': _utcnow()},
        )
        user['last_login'] = _utcnow()
        user['updated_at'] = _utcnow()

        return await self._issue_tokens(user)

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        payload = decode_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='无效的刷新令牌',
            )

        token_data = await token_repository.get_token(refresh_token)
        if not token_data or token_data.get('is_revoked'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='刷新令牌已失效',
            )

        user_id = payload.get('sub')
        user = await user_repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='用户不存在',
            )
        if not user.get('is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='用户已被禁用',
            )

        await token_repository.revoke_token(refresh_token)
        token_bundle = await self._issue_tokens(user)
        return {
            'access_token': token_bundle['access_token'],
            'refresh_token': token_bundle['refresh_token'],
            'token_type': token_bundle['token_type'],
            'expires_in': token_bundle['expires_in'],
        }

    async def logout(self, token: str) -> bool:
        return await token_repository.revoke_token(token)

    async def logout_all(self, user_id: str) -> int:
        return await token_repository.revoke_all_user_tokens(user_id)

    async def update_profile(
        self,
        user_id: str,
        nickname: str = None,
        avatar: str = None,
    ) -> bool:
        update_data: Dict[str, Any] = {'updated_at': _utcnow()}
        if nickname is not None:
            update_data['nickname'] = nickname
        if avatar is not None:
            update_data['avatar'] = avatar
        return await user_repository.update_one({'user_id': user_id}, update_data)

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = await user_repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='用户不存在',
            )
        if not verify_password(old_password, user.get('password', '')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='旧密码错误',
            )

        _validate_password_strength(new_password)
        return await user_repository.update_one(
            {'user_id': user_id},
            {'password': hash_password(new_password), 'updated_at': _utcnow()},
        )


auth_service = AuthService()
