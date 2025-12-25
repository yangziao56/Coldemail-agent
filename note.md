# notes.md — Cold Email Generator

## 0. 项目目标（一句话）

从两个人身上尽可能多的信息里，  
找到他们的**交集**和**可以互相提供的价值**，  
写出一封**真诚的第一封冷邮件**，帮他们建立真实的连接。

---

## 1. 版本演进

### v0 - JSON 输入

### v1.0 - PDF 简历解析

### v1.1 - 网络搜索获取 receiver 信息

### v1.2 - 切换到 Google Gemini API

### v2.0 (Current) - 智能向导式 Web 界面 🎉

**已实现功能：**

1. **Step 1: 目的选择**
   - 4个大类：学术陶瓷 ��、求职 💼、Coffee Chat ☕、其他 ✨
   - 4个领域：AI/ML 🤖、软件工程 💻、金融/Fintech 📈、其他 🔬
   - 支持自定义输入

2. **Step 2: 用户画像**
   - 有简历：上传 PDF 自动解析
   - 没简历：5 道选择题快速建立画像（每题 4 选项含自定义）

3. **Step 3: 找目标人选**
   - 手动输入：名字 + 领域
   - AI 推荐：最适配的 10 人 list，含契合度分析
   - 支持"继续生成"和"手动添加"

4. **Step 4: 生成邮件 + Regenerate**
   - 风格调整选项：更专业 / 更亲近 / 更简洁 / 更详细 / 自定义

**线上地址**: https://coldemail-agent.onrender.com/
**密码**: gogogochufalo

### v2.1 - 目标偏好问卷 & Field 下沉到 Step 3
- Step 1 只保留 purpose，移除 field 选择
- Step 3 选择“找匹配”时新增 5 个偏好问题：领域/专长（必选）、层级、组织类型、外展目标、知名度偏好
- 推荐生成：`find_target_recommendations` 使用 purpose + 偏好 + 领域提示词由 Gemini 产出候选人；搜索仍只用名字 + 领域

### v2.2 - 模型配置集中管理
- 新增 `config.py` 统一 `DEFAULT_MODEL`（可用环境变量 `GEMINI_MODEL` 覆盖），`email_agent.py`/`web_scraper.py`/`cli.py` 引用同一配置

---

## 2. 核心抽象（以后都尽量不改）

整个项目围绕一个核心函数：

> `(SenderProfile, ReceiverProfile, Goal) -> One sincere email`

- **SenderProfile**：关于发送者的一切有用信息  
- **ReceiverProfile**：关于接收者的一切可获得的信息  
- **Goal**：这封信要达到的目的（例如约 20 分钟电话 / 请教问题 / 求建议）

无论是：
- 投行新人 → 创业者 / 前辈  
- 工程师 → big tech mentor  
- 学生 → 教授  

都要能被抽象成这三样输入。

---

## 3. 技术栈

- **后端**: Python, Flask, Google Gemini API (gemini-2.0-flash)
- **前端**: HTML, CSS, JavaScript (原生)
- **部署**: Render.com + Gunicorn
- **PDF 解析**: PyPDF2
- **网络抓取**: BeautifulSoup4, Requests

---

## 4. 未来扩展方向

- [ ] 一对多（同一个 sender → 多个 receiver 批量生成）
- [ ] 邮件发送集成（直接发送而非复制）
- [ ] 用户账号系统（保存历史记录）
- [ ] 更多领域和场景模板
- [ ] 邮件效果追踪（打开率、回复率）

---

## 5. 最新改动快照

- 新增「全局模式切换」浮动入口：无论在向导哪个步骤，都能随时切换 Quick Start / Professional。切换会重置当前流程并自动进入对应起点（Quick 直接进入 Step 1，Professional 进入轨道选择）。
- Step 5 邮件展示改为可编辑：拆分 Subject / Body，并提供类似 ChatGPT 的内嵌 Copy 按钮（分别复制主题与正文）。
- Step 5 自定义语气（Custom）输入框加大，方便写更长的改写指令。
- Quick Start 的用户画像问卷改为“一次性生成 5 题”，前端本地逐题收集答案（不再每答一题就向后端请求下一题）。
- 右上角模式切换栏去掉重复的状态文字，只保留 `Quick` / `Professional` 两个按钮。
- `index_v2` 视觉风格升级为更“Apple-like”：浅色背景 + 玻璃拟态卡片 + 蓝色主色，整体更干净。
- Quick Start 的 5 道问卷题改为“一次性展示”，便于快速填写与回看。
- Quick Start：Step 2 先收集可选简历/LinkedIn/补充信息；仅当这些都为空时，才展示 5 道问卷作为兜底。
- Quick Start：可选简历上传改为拖拽/点击上传的 dropzone，和 Professional 统一交互风格。
- Quick Start：问卷题不再自动生成；当简历/LinkedIn/补充信息都为空时，点击 “Generate Questions” 才会生成并展示 5 题。
- Step 3（找 targets）：移除静态的 5 项偏好表单，仅保留动态偏好问答；推荐时默认使用 Step 1 的 field，并从动态问答中尽量提取更细分的 specialization。
- 动态问答增加硬性上限：到 `max_questions` 必定停止，避免出现 10+ 题的情况。
- Quick Start：进入 Step 1 会弹出一张简短教程（可选“不再提示”），帮助用户理解整个流程。
- Quick Start：教程文案补充“我们收集哪些信息/为什么需要这些信息/如何用来找人和写邮件”，让用户知其然也知其所以然。
- Step 3（找 targets）：新增可选「Targeting details」面板（理想人群描述、必须/排除关键词、地区语言时区、回复概率 vs 名气、参考样例、证据链接/摘录），用于更精准的推荐检索与排序。
- 推荐候选输出补齐可核验字段：每个候选可包含 `evidence` / `sources` / `uncertainty`，并在 Target Profile 弹窗中展示，方便用户快速核验而不是盲选。
- Step 4（生成邮件）：新增可选「Email instructions」输入（goal、单一 ask、可提供的 value、语气长度语言 constraints、hard rules 禁区、可引用 evidence），用于约束生成并减少虚构细节。
- Web enrichment：`/api/search-receiver` 返回 `raw_text` + `sources`，生成邮件时会把这些来源带入 prompt，提升引用的可追溯性。

---

## 6. 两个核心任务：找人 & 生成邮件（Context 优先）

这产品的上限，主要取决于两个任务能拿到多少**高质量、可验证的 context**，以及我们如何用结构化输入/输出把它“喂”给模型。

### 找人（推荐/搜索）

- 需要的 context：发送者画像（是谁/要什么/能给什么）+ 搜索意图（要找什么类型的人）+ 筛选条件（地区/层级/机构/行业细分）+ 证据（上传文档/链接/摘录）。
- 结果要可核验：每个候选给出匹配理由 + 证据来源 + 不确定性标注；没证据就别编细节。
- 工程上尽量拆开：检索候选 → 抽取结构化画像 → 打分排序（避免一个提示词做完全部导致不可控）。
- Wizard 侧可收集的结构化输入：理想人群描述、必须/排除关键词、地区语言时区、回复概率 vs 名气偏好、参考样例、证据链接/摘录（可选）。
- 推荐输出侧的最小可核验字段：`match_score` + `match_reason` + `evidence` + `sources` + `uncertainty`。

### 生成邮件（第一封冷邮件）

- 需要的 context：双方画像的可写事实点 + 明确 goal/ask（一个请求）+ 风格/长度/语言约束 + 禁止虚构规则。
- 邮件结构固定化：开场依据（为什么是对方）→ 交集/价值交换 → 明确请求（时长/可选时间）→ 退出选项。
- 个性化来源于证据点而不是夸赞；信息不足时先追问缺口或输出保守版本。
- Wizard 侧可收集的额外约束：goal、单一 ask、value、constraints、hard rules、可引用 evidence（可选）。
