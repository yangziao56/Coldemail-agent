# Finance Marketing Research → Benchmark 数据采集模板

这份文档的目标：用最小成本收集“真实用户输入 + 他们认为满意的输出标准”，并能直接转成 `benchmarks/finance/schema_v0.json`（v0.1）的 case。

如果你想要“可直接发出去”的问卷版本（Google Forms/Typeform 题目与选项都写好），见：`benchmarks/finance/survey_v1_google_forms.md`。

## 0) 你要先定的 3 个研究目标（写进问卷开头）

1) 用户在 finance 场景最常见的外联任务是什么？（找人/写信的组合）
2) 用户判断“好结果”的标准是什么？（可执行的、可验证的成功条件）
3) 真实世界输入通常包含什么证据？缺什么证据会导致失败？

## 1) 推荐研究方法（两条腿走路）

### A. 定性访谈（5–8 人）
- 目标：挖出“真实流程”和“决策标准”（为什么选这个人、为什么这句要这么写）。
- 产出：每人 1–2 条可转 benchmark 的样本（匿名化）。

### B. 问卷（20–50 份）
- 目标：量化场景分布（哪些需求最多）、收集更多输入样本。
- 产出：筛选出高质量样本进入 benchmark（优先有证据、有明确 ask、可复现）。

> 你现在先做 10 条 benchmark：建议先访谈 3–5 人 + 问卷 10–20 份，就够选出 10 条高质量样本。

## 2) 问卷结构（可直接复制到 Typeform/Google Forms）

### 2.1 Screener（筛选）
1) 你的角色更接近哪类？
   - IB / PE / VC / AM / Fintech / Corp Finance / Risk / Compliance / Other
2) 你过去 3 个月是否写过冷邮件/LinkedIn 外联？
   - 是 / 否
3) 你外联的主要目标是？
   - coffee chat / 求职内推 / 融资 / BD 合作 / 调研访谈 / 其它

### 2.2 场景采集（核心）
4) 请描述一次你最近真实发生的外联场景（可匿名）：
   - 你是谁（背景 2–4 句）？
   - 你想找什么人（岗位/机构/方向/地区）？
   - 你为什么找对方（1–2 个具体理由）？
   - 你希望对方做什么（一个清晰 ask：通话时长/时间窗口/替代选项）？
   - 你能提供什么价值（1–2 句）？

4.1) （可选，但强烈推荐）把“想找什么人”拆成可选结构化字段：
   - 目标岗位 titles（例如 Analyst/Associate/VP/Partner/Head of ...）：
   - seniority（例如 analyst/associate/manager/director）：
   - 机构类型 org_type（IB/PE/VC/AM/Fintech/Corp/Risk/Compliance）：
   - （banker）bank_tier（BB/EB/MM/Regional/Boutique）：
   - （banker）group（coverage: TMT/HC/FIG… 或 product: M&A/LevFin/ECM/DCM…）：
   - sector / stage（例如 Healthcare / Seed）：
   - 地区/语言/时区：
   - 你更希望通过什么渠道联系（email/LinkedIn/其他）：

4.2) （可选）把 ask 写成结构化：
   - ask 类型（call / coffee chat / deck feedback / intro / other）：
   - 时长（分钟）：
   - 时间范围（例如 next week / next 2 weeks）：
   - 可选时间窗（例如 Tue 2-5pm ET）：
   - 异步替代方案（例如“我可以先发 3 个问题邮件请教”）：
5) 你当时手头有哪些“可引用证据”？
   - 简历要点 / LinkedIn 摘录 / 官网团队页 / 文章链接 / 研报摘录 / 职位描述 / 其它
6) 请粘贴 1–3 条“可公开引用”的证据摘录（每条 1–3 句）+ 来源链接（如果有）
   - 提示：不要粘贴机密文件全文；只摘必要句子即可

### 2.3 “满意输出”定义（把主观变成可判定）
7) 你认为“找人结果”什么样算好？（多选 + 自填）
   - 候选与方向高度匹配
   - 候选信息足够我联系（职位/机构/链接）
   - 每个候选都有证据来源（可追溯）
   - 不确定就明确说不确定
   - 其它：____
8) 你认为“邮件结果”什么样算好？（多选 + 自填）
   - 结构清晰（why them → value → ask → opt-out）
   - 引用的事实都真实且来自我提供的信息
   - ask 很具体，读完能直接回复
   - 语气专业、不油腻、不过度吹捧
   - 其它：____
9) （可选）请提供一封你愿意发送的“参考邮件”（已匿名）
   - 可只给你认为最关键的 5–8 句

### 2.4 约束与禁区（finance 特别重要）
10) 你有哪些必须遵守的禁区？（多选 + 自填）
   - 不涉及任何投资建议
   - 不承诺收益/回报
   - 不暗示内幕信息
   - 不提及未公开客户/交易
   - 其它：____

### 2.5 允许我们如何使用这些信息（隐私）
11) 你是否同意我们将你的回答用于改进产品与内部评测？
   - 同意（仅内部、已匿名）/ 不同意

## 3) 访谈脚本（30 分钟）

1) 你最近一次外联的目标是什么？为什么重要？
2) 你是怎么“找人”的？你会用哪些信号判断“值得联系”？
3) 你在写第一封邮件时，最怕犯什么错？（虚构/合规/过长/过度销售）
4) 你会如何评价一封“好邮件”？能不能给一个你满意的例子（匿名化）？
5) 如果工具只能帮你一件事：找人 or 写信，你更希望先解决哪个？为什么？

## 4) 如何把问卷/访谈结果转成 benchmark case（最关键）

把每个受访者的“场景采集 + 证据摘录”整理成：
- `input.find_recommendations_request.sender_profile`：用 bullet 方式归纳（education/experiences/skills/projects/raw_text）
- `input.find_recommendations_request.preferences`：优先填结构化字段（`target_role_titles/seniority/org_type/bank_tier/group/sector/stage/recruiting_context/contact_channels`）+ `search_intent` + must-have/must-not + location + contactability
- `input.generate_email_request.receiver`：用公开证据/摘录填充 `raw_text` + `sources`，并尽量补 `evidence_snippets`
- `input.generate_email_request.email_spec`：把“满意标准”结构化（language/tone/长度/one-ask/value/hard rules/compliance guardrails）
- `input.generate_email_request.goal`：保留一段可读的自然语言 goal（方便人审与兼容现有接口）
- `expected.generate_email.assertions`：把“满意标准”翻译为可判定项（must_include / forbidden / required_elements / compliance）

如果你需要“预期找人输出”是稳定的：
- 把你调研得到的候选（或公开页面快照）整理成 `benchmark_context.candidate_pool`
- 在 `expected.find_recommendations.must_include_candidate_ids` 里写“必须出现的候选/类型”
