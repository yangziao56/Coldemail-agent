"""User Upload Storage Service.

保存用户上传的简历 PDF 和 target 信息。
存储路径: {DATA_DIR}/users/{日期}/{时间戳}_{session_id}/
  - resume.pdf (原始简历)
  - resume_profile.json (解析后的简历数据)
  - targets.json (target 信息列表)

DATA_DIR 由环境变量配置：
  - Render 生产环境: /var/data (Persistent Disk)
  - 本地开发: ./data
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from threading import Lock

# 从统一配置导入数据目录
from config import DATA_DIR

# 用户数据存储目录
USERS_DIR = DATA_DIR / "users"


def get_local_now() -> datetime:
    """获取本地时间（带时区）"""
    return datetime.now().astimezone()


def get_timestamp_str() -> str:
    """获取格式化的时间戳字符串 (用于文件名)"""
    now = get_local_now()
    return now.strftime("%H%M%S")


def get_date_str() -> str:
    """获取日期字符串 (用于文件夹名)"""
    now = get_local_now()
    return now.strftime("%Y-%m-%d")


@dataclass
class UserUploadRecord:
    """用户上传数据记录"""
    session_id: str
    timestamp: str = ""
    
    # 简历相关
    resume_filename: str = ""
    resume_profile: dict[str, Any] = field(default_factory=dict)
    
    # Target 信息
    targets: list[dict[str, Any]] = field(default_factory=list)
    
    # 用户基本信息
    user_info: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = get_local_now().isoformat()
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class UserUploadStorage:
    """用户上传数据存储服务（单例模式）"""
    
    _instance: Optional["UserUploadStorage"] = None
    _lock = Lock()
    
    def __new__(cls) -> "UserUploadStorage":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._sessions: dict[str, UserUploadRecord] = {}
        self._session_paths: dict[str, Path] = {}
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保存储目录存在"""
        USERS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_session_dir(self, session_id: str) -> Path:
        """获取 session 的存储目录"""
        if session_id in self._session_paths:
            return self._session_paths[session_id]
        
        date_str = get_date_str()
        time_str = get_timestamp_str()
        short_id = session_id[:8] if len(session_id) > 8 else session_id
        
        session_dir = USERS_DIR / date_str / f"{time_str}_{short_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        self._session_paths[session_id] = session_dir
        return session_dir
    
    def get_or_create_record(self, session_id: str) -> UserUploadRecord:
        """获取或创建 session 记录"""
        if session_id not in self._sessions:
            self._sessions[session_id] = UserUploadRecord(session_id=session_id)
        return self._sessions[session_id]
    
    def save_resume_pdf(
        self,
        session_id: str,
        pdf_file,  # FileStorage from Flask
        original_filename: str
    ) -> Path:
        """保存简历 PDF 文件"""
        record = self.get_or_create_record(session_id)
        session_dir = self._get_session_dir(session_id)
        
        # 保存原始文件名
        record.resume_filename = original_filename
        
        # 保存 PDF（使用固定名称方便查找）
        pdf_path = session_dir / "resume.pdf"
        pdf_file.save(str(pdf_path))
        
        # 同时保存一份带原始文件名的副本（如果名字不同）
        if original_filename and original_filename != "resume.pdf":
            original_path = session_dir / original_filename
            if not original_path.exists():
                shutil.copy(pdf_path, original_path)
        
        self._save_record(session_id)
        return pdf_path
    
    def save_resume_profile(
        self,
        session_id: str,
        profile: dict[str, Any]
    ) -> Path:
        """保存解析后的简历数据"""
        record = self.get_or_create_record(session_id)
        session_dir = self._get_session_dir(session_id)
        
        record.resume_profile = profile
        
        # 保存为 JSON
        profile_path = session_dir / "resume_profile.json"
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        
        self._save_record(session_id)
        return profile_path
    
    def save_targets(
        self,
        session_id: str,
        targets: list[dict[str, Any]]
    ) -> Path:
        """保存 target 信息"""
        record = self.get_or_create_record(session_id)
        session_dir = self._get_session_dir(session_id)
        
        record.targets = targets
        
        # 保存为 JSON
        targets_path = session_dir / "targets.json"
        with open(targets_path, 'w', encoding='utf-8') as f:
            json.dump(targets, f, ensure_ascii=False, indent=2)
        
        self._save_record(session_id)
        return targets_path
    
    def add_target(
        self,
        session_id: str,
        target: dict[str, Any]
    ) -> Path:
        """添加单个 target"""
        record = self.get_or_create_record(session_id)
        record.targets.append(target)
        return self.save_targets(session_id, record.targets)
    
    def update_user_info(
        self,
        session_id: str,
        user_info: dict[str, Any]
    ):
        """更新用户基本信息"""
        record = self.get_or_create_record(session_id)
        record.user_info.update(user_info)
        self._save_record(session_id)
    
    def _save_record(self, session_id: str):
        """保存完整记录到 metadata.json"""
        if session_id not in self._sessions:
            return
        
        record = self._sessions[session_id]
        session_dir = self._get_session_dir(session_id)
        
        metadata_path = session_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(record.to_json())
    
    def get_session_path(self, session_id: str) -> Optional[Path]:
        """获取 session 的存储路径"""
        return self._session_paths.get(session_id)


# 全局单例实例
user_upload_storage = UserUploadStorage()


# 便捷函数
def save_user_resume(
    session_id: str,
    pdf_file,
    original_filename: str,
    profile: dict[str, Any]
) -> dict[str, str]:
    """保存用户简历（PDF + 解析数据）"""
    pdf_path = user_upload_storage.save_resume_pdf(session_id, pdf_file, original_filename)
    profile_path = user_upload_storage.save_resume_profile(session_id, profile)
    
    return {
        "pdf_path": str(pdf_path),
        "profile_path": str(profile_path)
    }


def save_user_targets(
    session_id: str,
    targets: list[dict[str, Any]]
) -> str:
    """保存用户的 target 列表"""
    path = user_upload_storage.save_targets(session_id, targets)
    return str(path)


def add_user_target(
    session_id: str,
    target: dict[str, Any]
) -> str:
    """添加单个 target"""
    path = user_upload_storage.add_target(session_id, target)
    return str(path)
