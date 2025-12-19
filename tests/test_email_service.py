"""EmailService 单元测试。

测试覆盖:
- 邮件生成基本功能
- 不同风格参数
- 邮件改写功能
- 错误处理
"""

import pytest

from src.services.email_service import (
    EmailService,
    EmailStyle,
    EmailResult,
    EmailServiceError,
)
from src.models import SenderProfile, ReceiverProfile


class TestEmailServiceGenerate:
    """测试 EmailService.generate() 方法。"""
    
    def test_generate_returns_email_result(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 generate 返回正确的 EmailResult 类型。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.generate(
            sample_sender,
            sample_receiver,
            goal="Request a 20-min chat",
        )
        
        assert isinstance(result, EmailResult)
        assert result.subject != ""
        assert result.body != ""
        assert result.style == EmailStyle.PROFESSIONAL
    
    def test_generate_with_friendly_style(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 FRIENDLY 风格参数正确传递。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.generate(
            sample_sender,
            sample_receiver,
            goal="Request a chat",
            style=EmailStyle.FRIENDLY,
        )
        
        assert result.style == EmailStyle.FRIENDLY
    
    def test_generate_with_concise_style(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 CONCISE 风格参数正确传递。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.generate(
            sample_sender,
            sample_receiver,
            goal="Quick question",
            style=EmailStyle.CONCISE,
        )
        
        assert result.style == EmailStyle.CONCISE
    
    def test_generate_with_minimal_profiles(
        self,
        mock_llm_with_email_response,
        minimal_sender,
        minimal_receiver,
    ):
        """测试使用最小化 Profile 也能生成邮件。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.generate(
            minimal_sender,
            minimal_receiver,
            goal="General inquiry",
        )
        
        assert result.subject is not None
        assert result.body is not None
    
    def test_generate_calls_llm_once(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 generate 只调用 LLM 一次。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        service.generate(sample_sender, sample_receiver, goal="Test")
        
        assert mock_llm_with_email_response.call_count == 1


class TestEmailServiceRegenerate:
    """测试 EmailService.regenerate() 方法。"""
    
    def test_regenerate_basic(self, mock_llm_with_email_response):
        """测试基本改写功能。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.regenerate(
            original_email="Dear Sir, I am writing to inquire...",
        )
        
        assert isinstance(result, EmailResult)
        assert result.subject is not None
    
    def test_regenerate_with_style(self, mock_llm_with_email_response):
        """测试带风格参数的改写。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.regenerate(
            original_email="Hello, I wanted to reach out...",
            style=EmailStyle.PROFESSIONAL,
        )
        
        assert result.style == EmailStyle.PROFESSIONAL
    
    def test_regenerate_with_custom_instruction(self, mock_llm_with_email_response):
        """测试自定义指令改写。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        result = service.regenerate(
            original_email="Hi there, quick question...",
            custom_instruction="Make it more formal and add a proper greeting",
        )
        
        assert result.style == EmailStyle.CUSTOM


class TestEmailServiceErrorHandling:
    """测试 EmailService 错误处理。"""
    
    def test_generate_raises_on_invalid_json(self, mock_llm, sample_sender, sample_receiver):
        """测试 LLM 返回无效 JSON 时抛出 EmailServiceError。"""
        mock_llm.response = "This is not valid JSON"
        service = EmailService(llm_service=mock_llm)
        
        with pytest.raises(EmailServiceError) as exc_info:
            service.generate(sample_sender, sample_receiver, goal="Test")
        
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_generate_raises_on_llm_failure(self, mock_llm, sample_sender, sample_receiver):
        """测试 LLM 调用失败时抛出 EmailServiceError。"""
        mock_llm.should_fail = True
        mock_llm.max_failures = 999  # 总是失败
        service = EmailService(llm_service=mock_llm)
        
        with pytest.raises(EmailServiceError) as exc_info:
            service.generate(sample_sender, sample_receiver, goal="Test")
        
        assert "failed" in str(exc_info.value).lower()
    
    def test_regenerate_raises_on_invalid_json(self, mock_llm):
        """测试改写时 LLM 返回无效 JSON 抛出异常。"""
        mock_llm.response = "{broken json"
        service = EmailService(llm_service=mock_llm)
        
        with pytest.raises(EmailServiceError):
            service.regenerate(original_email="Test email")


class TestEmailServicePromptBuilding:
    """测试 EmailService 内部 prompt 构建。"""
    
    def test_prompt_includes_sender_info(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 prompt 包含 sender 信息。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        # 调用 generate 并检查 prompt
        # 由于是 mock，我们可以通过构建 prompt 方法单独测试
        prompt = service._build_generation_prompt(
            sample_sender,
            sample_receiver,
            "Test goal",
            EmailStyle.PROFESSIONAL,
        )
        
        assert sample_sender.name in prompt
        assert "MIT" in prompt  # education
        assert "Google" in prompt  # experience
    
    def test_prompt_includes_receiver_info(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 prompt 包含 receiver 信息。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        prompt = service._build_generation_prompt(
            sample_sender,
            sample_receiver,
            "Test goal",
            EmailStyle.PROFESSIONAL,
        )
        
        assert sample_receiver.name in prompt
        assert "Stanford" in prompt
    
    def test_prompt_includes_goal(
        self,
        mock_llm_with_email_response,
        sample_sender,
        sample_receiver,
    ):
        """测试 prompt 包含目标。"""
        service = EmailService(llm_service=mock_llm_with_email_response)
        
        goal = "Request a 30-minute informational interview"
        prompt = service._build_generation_prompt(
            sample_sender,
            sample_receiver,
            goal,
            EmailStyle.PROFESSIONAL,
        )
        
        assert goal in prompt
