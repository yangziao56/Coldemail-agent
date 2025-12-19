"""测试配置和共享 Fixtures。"""

import pytest
from unittest.mock import MagicMock

from src.models import SenderProfile, ReceiverProfile, Recommendation


# ============================================================================
# Mock Services
# ============================================================================

class MockLLMService:
    """测试用 Mock LLM 服务。
    
    可以通过设置 response 属性来控制返回值。
    可以通过设置 should_fail 来模拟失败。
    """
    
    def __init__(self):
        self.response = '{"subject": "Test", "body": "Test body"}'
        self.should_fail = False
        self.fail_count = 0
        self.max_failures = 0
        self.call_count = 0
    
    def call(self, prompt: str, *, json_mode: bool = False) -> str:
        self.call_count += 1
        
        if self.should_fail:
            if self.fail_count < self.max_failures:
                self.fail_count += 1
                raise Exception("Mock LLM failure")
        
        return self.response
    
    def call_with_search(self, prompt: str, *, json_mode: bool = False) -> str:
        return self.call(prompt, json_mode=json_mode)
    
    def reset(self):
        """重置状态。"""
        self.call_count = 0
        self.fail_count = 0


# ============================================================================
# Profile Fixtures
# ============================================================================

@pytest.fixture
def sample_sender() -> SenderProfile:
    """创建示例 Sender Profile。"""
    return SenderProfile(
        name="Alice Zhang",
        raw_text="Alice Zhang is a software engineer...",
        education=["MIT Computer Science BS 2020", "Stanford AI MS 2022"],
        experiences=[
            "Google Software Engineer 2022-present",
            "Meta Intern 2021",
        ],
        skills=["Python", "Machine Learning", "System Design"],
        projects=["Open source ML framework contributor"],
        motivation="Seeking career advice in AI research",
        ask="Would appreciate a 20-minute chat about transitioning to research",
    )


@pytest.fixture
def sample_receiver() -> ReceiverProfile:
    """创建示例 Receiver Profile。"""
    return ReceiverProfile(
        name="Dr. Andrew Ng",
        raw_text="Andrew Ng is a renowned AI researcher...",
        education=["MIT PhD", "CMU BS"],
        experiences=[
            "Stanford Professor",
            "Google Brain Founder",
            "Coursera Co-founder",
        ],
        skills=["Deep Learning", "Online Education", "AI Research"],
        projects=["deeplearning.ai", "Coursera ML Course"],
        context="Leading AI researcher and educator",
        sources=["https://www.andrewng.org/"],
    )


@pytest.fixture
def minimal_sender() -> SenderProfile:
    """创建最小化 Sender Profile（用于边界测试）。"""
    return SenderProfile(
        name="Unknown",
        raw_text="",
        education=[],
        experiences=[],
        skills=[],
        projects=[],
        motivation="",
        ask="",
    )


@pytest.fixture
def minimal_receiver() -> ReceiverProfile:
    """创建最小化 Receiver Profile（用于边界测试）。"""
    return ReceiverProfile(
        name="Unknown",
        raw_text="",
        education=[],
        experiences=[],
        skills=[],
        projects=[],
    )


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def mock_llm() -> MockLLMService:
    """创建 Mock LLM 服务。"""
    return MockLLMService()


@pytest.fixture
def mock_llm_with_profile_response(mock_llm: MockLLMService) -> MockLLMService:
    """创建返回 Profile JSON 的 Mock LLM。"""
    mock_llm.response = '''{
        "name": "Test User",
        "education": ["University A"],
        "experiences": ["Company B"],
        "skills": ["Skill C"],
        "projects": ["Project D"]
    }'''
    return mock_llm


@pytest.fixture
def mock_llm_with_email_response(mock_llm: MockLLMService) -> MockLLMService:
    """创建返回 Email JSON 的 Mock LLM。"""
    mock_llm.response = '''{
        "subject": "Seeking Advice on AI Research Career",
        "body": "Dear Dr. Ng,\\n\\nI hope this email finds you well..."
    }'''
    return mock_llm


@pytest.fixture
def mock_llm_with_recommendations(mock_llm: MockLLMService) -> MockLLMService:
    """创建返回推荐 JSON 的 Mock LLM。"""
    mock_llm.response = '''{
        "recommendations": [
            {
                "name": "Dr. Jane Smith",
                "title": "AI Research Director",
                "organization": "OpenAI",
                "field": "Machine Learning",
                "match_score": 85,
                "match_reason": "Strong ML background, mentorship experience",
                "contact_info": "jane@openai.com",
                "sources": ["https://openai.com/team"],
                "uncertainty": ""
            }
        ]
    }'''
    return mock_llm


# ============================================================================
# Test Utilities
# ============================================================================

@pytest.fixture
def temp_pdf(tmp_path):
    """创建临时 PDF 文件（空白）。
    
    注意：这只是占位符。实际 PDF 测试需要真实 PDF 文件。
    """
    pdf_path = tmp_path / "test.pdf"
    # 创建一个最小的有效 PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path
