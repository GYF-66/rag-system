# -*- coding: utf-8 -*-
"""Authentication routes for registration, login and profile management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from auth import auth_service, decode_token, get_current_user, security
from models import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserInfo,
)
from rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/auth', tags=['auth'])


@router.post('/register', response_model=LoginResponse)
@limiter.limit('5/minute')
async def register(payload: RegisterRequest, request: Request) -> LoginResponse:
    result = await auth_service.register(
        username=payload.username,
        password=payload.password,
        nickname=payload.nickname,
        avatar=payload.avatar,
    )
    return LoginResponse(**result)


@router.post('/login', response_model=LoginResponse)
@limiter.limit('5/minute')
async def login(payload: LoginRequest, request: Request) -> LoginResponse:
    result = await auth_service.login(username=payload.username, password=payload.password)
    return LoginResponse(**result)


@router.post('/refresh', response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest) -> TokenResponse:
    result = await auth_service.refresh_token(payload.refresh_token)
    return TokenResponse(**result)


@router.post('/logout')
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    success = await auth_service.logout(token)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='登出失败')
    return {'status': 'success', 'message': '已登出'}


@router.post('/logout-all')
async def logout_all(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='无效的认证凭据')

    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token 中缺少用户信息')

    count = await auth_service.logout_all(user_id)
    return {'status': 'success', 'message': f'已登出 {count} 个设备'}


@router.get('/me', response_model=UserInfo)
async def get_current_user_info(user: dict = Depends(get_current_user)) -> UserInfo:
    return UserInfo(
        user_id=user.get('user_id'),
        username=user.get('username'),
        nickname=user.get('nickname'),
        avatar=user.get('avatar'),
        created_at=user.get('created_at'),
        updated_at=user.get('updated_at'),
        last_login=user.get('last_login'),
    )


@router.put('/profile')
async def update_profile(request: UpdateProfileRequest, user: dict = Depends(get_current_user)) -> dict:
    success = await auth_service.update_profile(
        user_id=user['user_id'],
        nickname=request.nickname,
        avatar=request.avatar,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='资料更新失败')
    return {'status': 'success', 'message': '资料更新成功'}


@router.post('/change-password')
async def change_password(request: ChangePasswordRequest, user: dict = Depends(get_current_user)) -> dict:
    success = await auth_service.change_password(
        user_id=user['user_id'],
        old_password=request.old_password,
        new_password=request.new_password,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='密码修改失败')
    return {'status': 'success', 'message': '密码修改成功'}
