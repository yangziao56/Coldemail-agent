"""Profile 数据模型单元测试。"""

import pytest

from src.models import ProfileBase, SenderProfile, ReceiverProfile


class TestProfileBase:
    """测试 ProfileBase 数据类。"""
    
    def test_create_profile_base(self):
        """测试创建 ProfileBase。"""
        profile = ProfileBase(
            name="Test User",
            raw_text="Some raw text",
            education=["MIT"],
            experiences=["Google"],
            skills=["Python"],
            projects=["Project A"],
        )
        
        assert profile.name == "Test User"
        assert profile.raw_text == "Some raw text"
        assert "MIT" in profile.education
    
    def test_profile_base_to_dict(self):
        """测试 to_dict 方法。"""
        profile = ProfileBase(
            name="Test",
            raw_text="text",
            education=["School"],
            experiences=["Job"],
            skills=["Skill"],
            projects=["Project"],
        )
        
        data = profile.to_dict()
        
        assert data["name"] == "Test"
        assert data["education"] == ["School"]
        assert isinstance(data, dict)
    
    def test_profile_base_from_dict(self):
        """测试 from_dict 方法。"""
        data = {
            "name": "From Dict",
            "raw_text": "raw",
            "education": ["Edu"],
            "experiences": ["Exp"],
            "skills": ["Skill"],
            "projects": ["Proj"],
        }
        
        profile = ProfileBase.from_dict(data)
        
        assert profile.name == "From Dict"
        assert profile.education == ["Edu"]
    
    def test_profile_base_from_dict_with_missing_fields(self):
        """测试 from_dict 处理缺失字段。"""
        data = {"name": "Partial"}
        
        profile = ProfileBase.from_dict(data)
        
        assert profile.name == "Partial"
        assert profile.raw_text == ""
        assert profile.education == []
    
    def test_profile_base_default_values(self):
        """测试默认值。"""
        profile = ProfileBase(name="Min", raw_text="")
        
        assert profile.education == []
        assert profile.experiences == []
        assert profile.skills == []
        assert profile.projects == []


class TestSenderProfile:
    """测试 SenderProfile 数据类。"""
    
    def test_create_sender_profile(self):
        """测试创建 SenderProfile。"""
        profile = SenderProfile(
            name="Sender",
            raw_text="text",
            education=[],
            experiences=[],
            skills=[],
            projects=[],
            motivation="Career advice",
            ask="20 min chat",
        )
        
        assert profile.motivation == "Career advice"
        assert profile.ask == "20 min chat"
    
    def test_sender_profile_to_dict_includes_extra_fields(self):
        """测试 to_dict 包含 motivation 和 ask。"""
        profile = SenderProfile(
            name="Test",
            raw_text="",
            education=[],
            experiences=[],
            skills=[],
            projects=[],
            motivation="Learn",
            ask="Help",
        )
        
        data = profile.to_dict()
        
        assert "motivation" in data
        assert "ask" in data
        assert data["motivation"] == "Learn"
    
    def test_sender_profile_from_dict(self):
        """测试 from_dict 方法。"""
        data = {
            "name": "Sender",
            "raw_text": "",
            "education": [],
            "experiences": [],
            "skills": [],
            "projects": [],
            "motivation": "Networking",
            "ask": "Advice",
        }
        
        profile = SenderProfile.from_dict(data)
        
        assert profile.motivation == "Networking"
        assert profile.ask == "Advice"


class TestReceiverProfile:
    """测试 ReceiverProfile 数据类。"""
    
    def test_create_receiver_profile(self):
        """测试创建 ReceiverProfile。"""
        profile = ReceiverProfile(
            name="Receiver",
            raw_text="text",
            education=[],
            experiences=[],
            skills=[],
            projects=[],
            context="AI researcher",
            sources=["https://example.com"],
        )
        
        assert profile.context == "AI researcher"
        assert "https://example.com" in profile.sources
    
    def test_receiver_profile_context_optional(self):
        """测试 context 是可选的。"""
        profile = ReceiverProfile(
            name="Test",
            raw_text="",
            education=[],
            experiences=[],
            skills=[],
            projects=[],
        )
        
        assert profile.context is None
        assert profile.sources == []
    
    def test_receiver_profile_to_dict(self):
        """测试 to_dict 方法。"""
        profile = ReceiverProfile(
            name="Test",
            raw_text="",
            education=[],
            experiences=[],
            skills=[],
            projects=[],
            context="Context",
            sources=["url1", "url2"],
        )
        
        data = profile.to_dict()
        
        assert data["context"] == "Context"
        assert data["sources"] == ["url1", "url2"]
    
    def test_receiver_profile_from_dict(self):
        """测试 from_dict 方法。"""
        data = {
            "name": "Receiver",
            "raw_text": "",
            "context": "Professor",
            "sources": ["https://university.edu"],
        }
        
        profile = ReceiverProfile.from_dict(data)
        
        assert profile.context == "Professor"
        assert profile.sources == ["https://university.edu"]
