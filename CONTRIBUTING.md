# 实习生开发指南 (Intern Development Guide)

> 本文档为实习生参与项目开发提供标准化工作流程。所有开发工作必须遵循此流程。

## 📋 目录

1. [项目架构概览](#项目架构概览)
2. [开发环境设置](#开发环境设置)
3. [Git 工作流程](#git-工作流程)
4. [单元模块开发流程](#单元模块开发流程)
5. [测试规范](#测试规范)
6. [代码审查清单](#代码审查清单)
7. [权限边界](#权限边界)

---

## 项目架构概览

```
Coldemail-agent/
├── app.py                    # 🔒 Flask 路由层 (禁止直接修改)
├── config.py                 # 🔒 全局配置 (禁止直接修改)
├── src/
│   ├── models/               # ✅ 数据模型 (可开发)
│   │   ├── profile.py        # Profile 数据类
│   │   └── recommendation.py # Recommendation 数据类
│   ├── services/             # ✅ 业务逻辑层 (可开发)
│   │   ├── llm_service.py    # 🔒 LLM 调用抽象 (需 Review)
│   │   ├── profile_service.py   # ✅ Profile 解析服务
│   │   ├── email_service.py     # ✅ 邮件生成服务
│   │   └── recommendation_service.py # 🔒 推荐服务 (需 Review)
│   ├── email_agent.py        # 🔒 旧核心模块 (逐步迁移中)
│   └── web_scraper.py        # 🔒 Web 爬虫 (禁止修改)
├── templates/                # 🔒 前端模板 (禁止直接修改)
├── tests/                    # ✅ 测试目录 (可开发)
└── docs/modules/             # ✅ 模块文档 (必须更新)
```

**图例**:
- ✅ 可独立开发
- 🔒 需要 Senior Review 或禁止修改

---

## 开发环境设置

### 1. Fork 仓库 (必须)

```bash
# 实习生从主仓库 Fork 到自己账户，不要直接 clone 主仓库
# 在 GitHub 上点击 Fork 按钮

# Clone 你的 Fork
git clone https://github.com/<YOUR_USERNAME>/Coldemail-agent.git
cd Coldemail-agent

# 添加上游仓库
git remote add upstream https://github.com/yangziao56/Coldemail-agent.git
```

### 2. 环境配置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install pytest pytest-cov  # 测试依赖

# 配置环境变量 (不要提交到 Git!)
export GEMINI_API_KEY="your-api-key"  # 向 Senior 索取测试 Key
```

### 3. 验证环境

```bash
# 运行测试确保环境正常
pytest tests/ -v

# 本地启动应用 (仅用于集成测试)
python app.py
```

---

## Git 工作流程

### 分支命名规范

```
feature/intern-<name>-<module>-<brief-description>
例如: feature/intern-xiaoming-email-service-add-retry
```

### 标准开发流程

```bash
# 1. 同步上游最新代码
git fetch upstream
git checkout main
git merge upstream/main

# 2. 创建功能分支
git checkout -b feature/intern-xiaoming-email-service-add-retry

# 3. 开发 + 测试 (循环)
# ... 编码 ...
pytest tests/test_email_service.py -v
git add .
git commit -m "feat(email): add retry logic for LLM calls"

# 4. 推送到你的 Fork
git push origin feature/intern-xiaoming-email-service-add-retry

# 5. 在 GitHub 创建 Pull Request → 主仓库的 main 分支
```

### Commit 规范

```
<type>(<scope>): <description>

type: feat | fix | test | docs | refactor | style
scope: email | profile | recommendation | llm | tests
description: 简短描述，动词开头，不超过 50 字符
```

**示例**:
```
feat(email): add friendly style option
fix(profile): handle empty PDF correctly
test(email): add unit tests for regeneration
docs(email): update interface documentation
```

---

## 单元模块开发流程

### Phase 1: 接收任务

1. Senior 在 `docs/modules/` 创建任务文档 (如 `TASK-001-email-retry.md`)
2. 实习生阅读文档，确认理解需求
3. 在 GitHub Issue 或飞书确认接收

### Phase 2: 设计确认

1. 实习生编写简要设计方案 (修改哪些文件、添加哪些函数)
2. 提交设计到任务文档的 "设计方案" 部分
3. 等待 Senior 确认后再开始编码

### Phase 3: 开发

1. **先写测试** (TDD 推荐)
2. 实现功能代码
3. 本地运行测试
4. 更新任务文档的 "实现说明" 部分

### Phase 4: 提交审查

1. 创建 Pull Request
2. 填写 PR 模板
3. 等待 Senior Review
4. 根据反馈修改
5. 合并后关闭任务

---

## 测试规范

### 测试文件命名

```
tests/
├── test_models.py              # 数据模型测试
├── test_profile_service.py     # Profile 服务测试
├── test_email_service.py       # Email 服务测试
└── conftest.py                 # 测试配置和 fixtures
```

### 测试示例

```python
# tests/test_email_service.py

import pytest
from src.services.email_service import EmailService, EmailStyle, EmailServiceError
from src.models import SenderProfile, ReceiverProfile


class MockLLMService:
    """测试用 Mock LLM 服务"""
    
    def call(self, prompt: str, *, json_mode: bool = False) -> str:
        return '{"subject": "Test Subject", "body": "Test Body"}'
    
    def call_with_search(self, prompt: str, *, json_mode: bool = False) -> str:
        return self.call(prompt, json_mode=json_mode)


@pytest.fixture
def email_service():
    """创建带 Mock LLM 的 EmailService"""
    return EmailService(llm_service=MockLLMService())


@pytest.fixture
def sample_sender():
    return SenderProfile(
        name="Test Sender",
        raw_text="test",
        education=["MIT"],
        experiences=["Google"],
        skills=["Python"],
        projects=[],
        motivation="Learn",
        ask="Advice",
    )


@pytest.fixture
def sample_receiver():
    return ReceiverProfile(
        name="Test Receiver",
        raw_text="test",
        education=["Stanford"],
        experiences=["Meta"],
        skills=["AI"],
        projects=[],
    )


class TestEmailService:
    """EmailService 单元测试"""
    
    def test_generate_returns_email_result(self, email_service, sample_sender, sample_receiver):
        """测试 generate 返回正确格式"""
        result = email_service.generate(
            sample_sender,
            sample_receiver,
            goal="Request a chat",
        )
        
        assert result.subject == "Test Subject"
        assert result.body == "Test Body"
        assert result.style == EmailStyle.PROFESSIONAL
    
    def test_generate_with_friendly_style(self, email_service, sample_sender, sample_receiver):
        """测试 friendly 风格参数传递"""
        result = email_service.generate(
            sample_sender,
            sample_receiver,
            goal="Request a chat",
            style=EmailStyle.FRIENDLY,
        )
        
        assert result.style == EmailStyle.FRIENDLY
    
    def test_regenerate_with_custom_instruction(self, email_service):
        """测试自定义指令改写"""
        result = email_service.regenerate(
            original_email="Hello, I am writing to...",
            custom_instruction="Make it shorter",
        )
        
        assert result.subject is not None
        assert result.body is not None


class TestEmailServiceErrorHandling:
    """EmailService 错误处理测试"""
    
    def test_generate_raises_on_invalid_json(self):
        """测试 LLM 返回无效 JSON 时抛出异常"""
        
        class BrokenLLMService:
            def call(self, prompt: str, *, json_mode: bool = False) -> str:
                return "not valid json"
        
        service = EmailService(llm_service=BrokenLLMService())
        
        with pytest.raises(EmailServiceError):
            service.generate(
                SenderProfile(name="A", raw_text="", education=[], experiences=[], skills=[], projects=[], motivation="", ask=""),
                ReceiverProfile(name="B", raw_text="", education=[], experiences=[], skills=[], projects=[]),
                goal="test",
            )
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_email_service.py -v

# 运行带覆盖率
pytest tests/ --cov=src/services --cov-report=html

# 只运行某个测试类
pytest tests/test_email_service.py::TestEmailService -v
```

---

## 代码审查清单

### 实习生自查 (提交 PR 前)

- [ ] 所有测试通过 (`pytest tests/ -v`)
- [ ] 代码有类型标注
- [ ] 函数有 docstring
- [ ] 没有硬编码的 API Key 或密码
- [ ] 没有修改 🔒 标记的文件
- [ ] 更新了相关文档
- [ ] Commit message 符合规范

### Senior 审查

- [ ] 代码符合接口契约
- [ ] 错误处理完善
- [ ] 测试覆盖关键路径
- [ ] 没有引入安全风险
- [ ] 性能可接受

---

## 权限边界

### ✅ 实习生可以做

1. 在 `src/services/` 下开发新功能
2. 在 `src/models/` 下添加数据模型
3. 在 `tests/` 下编写测试
4. 在 `docs/modules/` 下更新文档
5. 修复已分配的 Bug

### ❌ 实习生不可以做

1. 直接修改 `app.py` (Flask 路由)
2. 直接修改 `config.py` (全局配置)
3. 直接修改 `templates/` (前端模板)
4. 直接修改 `src/email_agent.py` (旧核心模块)
5. 直接 push 到 `main` 分支
6. 合并自己的 PR (需要 Senior 审批)

### 🟡 需要 Senior 协助

1. 修改 LLM 调用逻辑 (`llm_service.py`)
2. 修改推荐系统 (`recommendation_service.py`)
3. 添加新的 API 端点
4. 修改数据库/缓存逻辑
5. 修改部署配置

---

## 常见问题

### Q: 我需要调用 LLM 测试，但没有 API Key？

使用 Mock 服务进行单元测试。如需集成测试，向 Senior 索取测试用 Key。

### Q: 我的改动需要修改 app.py 怎么办？

在 PR 中说明需求，Senior 会帮你添加路由或进行必要修改。

### Q: 测试失败了但我不知道为什么？

1. 先阅读错误信息
2. 检查是否环境问题
3. 在飞书群提问，附上错误截图

### Q: 我发现了一个 Bug，不在我的任务范围内？

在 GitHub 创建 Issue，描述复现步骤，等待 Senior 分配。

---

## 联系方式

- **技术问题**: 飞书群 / GitHub Issue
- **紧急问题**: 直接联系 Senior
- **代码审查**: GitHub PR 评论
