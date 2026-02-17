# -*- coding: utf-8 -*-
"""
会话管理模块
负责用户会话的创建、存储和检索
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import SESSIONS_DIR, MEMORY_DIR, MAX_HISTORY_TURNS


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.sessions_dir = SESSIONS_DIR
        self.memory_dir = MEMORY_DIR

    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        创建新会话

        Args:
            user_id: 用户ID

        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())

        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': []
        }

        self._save_session(session_id, session_data)

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话数据，不存在返回None
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取会话失败: {e}")
            return None

    def update_session(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str
    ) -> bool:
        """
        更新会话，添加新消息

        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_message: 助手回复

        Returns:
            更新是否成功
        """
        session_data = self.get_session(session_id)

        if not session_data:
            return False

        # 添加新消息
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
        if len(session_data['messages']) > MAX_HISTORY_TURNS * 2:
            session_data['messages'] = session_data['messages'][-MAX_HISTORY_TURNS * 2:]

        # 更新时间
        session_data['updated_at'] = datetime.now().isoformat()

        self._save_session(session_id, session_data)

        return True

    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        获取会话历史

        Args:
            session_id: 会话ID

        Returns:
            消息历史列表
        """
        session_data = self.get_session(session_id)

        if not session_data:
            return []

        return session_data.get('messages', [])

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            删除是否成功
        """
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return False

        try:
            session_file.unlink()
            return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False

    def list_user_sessions(self, user_id: str) -> List[Dict]:
        """
        列出用户的所有会话

        Args:
            user_id: 用户ID

        Returns:
            会话列表
        """
        sessions = []

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                if session_data.get('user_id') == user_id:
                    sessions.append({
                        'session_id': session_data['session_id'],
                        'created_at': session_data['created_at'],
                        'updated_at': session_data['updated_at'],
                        'message_count': len(session_data.get('messages', []))
                    })
            except Exception as e:
                print(f"读取会话失败: {e}")

        # 按更新时间倒序排序
        sessions.sort(key=lambda x: x['updated_at'], reverse=True)

        return sessions

    def _save_session(self, session_id: str, session_data: Dict):
        """保存会话到文件"""
        session_file = self.sessions_dir / f"{session_id}.json"

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)


class MemoryManager:
    """记忆管理器 - 跨会话学习能力"""

    def __init__(self):
        self.memory_dir = MEMORY_DIR

    def save_learned_knowledge(
        self,
        user_id: str,
        topic: str,
        knowledge: str
    ):
        """
        保存学到的知识

        Args:
            user_id: 用户ID
            topic: 主题
            knowledge: 知识内容
        """
        memory_file = self.memory_dir / f"{user_id}.json"

        memory_data = {}

        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)

        if 'learned_knowledge' not in memory_data:
            memory_data['learned_knowledge'] = {}

        memory_data['learned_knowledge'][topic] = {
            'content': knowledge,
            'learned_at': datetime.now().isoformat()
        }

        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)

    def get_user_memory(self, user_id: str) -> Dict:
        """
        获取用户记忆

        Args:
            user_id: 用户ID

        Returns:
            用户记忆数据
        """
        memory_file = self.memory_dir / f"{user_id}.json"

        if not memory_file.exists():
            return {}

        with open(memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)


# 全局实例
session_manager = SessionManager()
memory_manager = MemoryManager()