# -*- coding: utf-8 -*-
"""
空间管理 API 路由

使用方法：
    from routers import spaces_router
    app.include_router(spaces_router, prefix="/api/v1", tags=["spaces"])

API 端点：
    POST   /api/v1/spaces        - 创建空间
    GET    /api/v1/spaces        - 获取空间列表
    GET    /api/v1/spaces/{id}   - 获取单个空间
    DELETE /api/v1/spaces/{id}   - 删除空间
"""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status
from pymongo import DESCENDING

from database import get_database
from models import SpaceCreate, SpaceResponse, SpaceListResponse


router = APIRouter()


@router.post("/spaces", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(space: SpaceCreate):
    """
    创建新空间

    Args:
        space: 空间创建数据

    Returns:
        SpaceResponse: 创建的空间信息
    """
    db = await get_database()
    collection = db.spaces

    # 生成空间 ID
    space_id = str(uuid.uuid4())

    # 构建空间文档
    space_doc = {
        "_id": space_id,
        "id": space_id,
        "name": space.name,
        "description": space.description,
        "icon": space.icon,
        "color": space.color,
        "itemCount": 0,
        "updatedAt": datetime.now()
    }

    # 插入数据库
    result = await collection.insert_one(space_doc)

    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建空间失败"
        )

    return SpaceResponse(
        id=space_doc["id"],
        name=space_doc["name"],
        description=space_doc["description"],
        icon=space_doc["icon"],
        color=space_doc["color"],
        item_count=space_doc["itemCount"],
        updated_at=space_doc["updatedAt"]
    )


@router.get("/spaces", response_model=SpaceListResponse)
async def get_spaces():
    """
    获取空间列表

    Returns:
        SpaceListResponse: 空间列表
    """
    db = await get_database()
    collection = db.spaces

    # 查询所有空间，按更新时间倒序
    cursor = collection.find().sort("updatedAt", DESCENDING)

    spaces = []
    async for doc in cursor:
        spaces.append(SpaceResponse(
            id=doc["id"],
            name=doc["name"],
            description=doc.get("description"),
            icon=doc["icon"],
            color=doc["color"],
            item_count=doc.get("itemCount", 0),
            updated_at=doc["updatedAt"]
        ))

    return SpaceListResponse(spaces=spaces, total=len(spaces))


@router.get("/spaces/{space_id}", response_model=SpaceResponse)
async def get_space(space_id: str):
    """
    获取单个空间详情

    Args:
        space_id: 空间 ID

    Returns:
        SpaceResponse: 空间详情
    """
    db = await get_database()
    collection = db.spaces

    doc = await collection.find_one({"id": space_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="空间不存在"
        )

    return SpaceResponse(
        id=doc["id"],
        name=doc["name"],
        description=doc.get("description"),
        icon=doc["icon"],
        color=doc["color"],
        item_count=doc.get("itemCount", 0),
        updated_at=doc["updatedAt"]
    )


@router.delete("/spaces/{space_id}")
async def delete_space(space_id: str):
    """
    删除空间

    Args:
        space_id: 空间 ID

    Returns:
        dict: 删除结果
    """
    db = await get_database()
    collection = db.spaces

    result = await collection.delete_one({"id": space_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="空间不存在"
        )

    return {"status": "success", "message": "空间已删除"}