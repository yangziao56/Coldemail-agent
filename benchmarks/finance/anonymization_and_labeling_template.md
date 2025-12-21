# 匿名化 & 标注模板（Finance Benchmark）

目标：把“真实用户的一次找人/写信需求”整理成一条可复现的 benchmark case，并且避免泄露隐私或机密信息。

## 1) 安全与匿名化规则（必须）

### 必须移除 / 替换
- 个人信息：真实姓名、邮箱、手机号、微信、精确住址、身份证件信息。
- 公司机密：未公开客户名称、未公开交易细节、未公开财务数据、内部文档全文。
- 可回溯身份的组合信息：过多精确时间线 + 唯一项目细节（建议泛化为“某券商/某项目/某地区”）。

### 推荐做法
- 人名用占位：`Person A` / `Target 1` / `Hiring Manager`。
- 机构用占位：`Example Bank` / `Example VC` / `Mid-market PE`。
- 证据用“可公开材料”：公司官网团队页、公开文章、公开职位描述、公开 LinkedIn 摘要（仅摘录必要句子）。

## 2) 一条样本的最小组成

你最终要产出一个 JSON 对象（参考 `benchmarks/finance/schema_v0.json`，v0.1），至少包含。

> 重要：当前 Web App 的 API 并不会直接消费所有 v0.1 字段（例如 `email_spec`、`candidate_pool` 等）。  
> 如果你要“拿真实样本直接跑现有接口”，请把这些结构化信息**合并进现有已使用字段**（见下方提示）。

### A. 找人输入（对应 `/api/find-recommendations`）
- `purpose`：用户要做什么（coffee chat / job seeking / partnership / other）
- `field`：Finance / Fintech 等
- `sender_profile`：发送者背景（尽量结构化）
- `preferences`：理想人群描述（search_intent）、must-have / must-not、地区语言、reply vs prestige 等（这些会进 prompt）

（可选但建议收集）banker 维度如 `bank_tier/group/seniority/contact_channels/recruiting_context`：目前不会自动进 prompt，建议你把它们也写进 `search_intent` 或 `extra`，这样现有 agent 能用上。

### B. 写信输入（对应 `/api/generate-email`）
- `sender`：发送者结构化画像（同上）
- `receiver`：收件人画像（来自公开证据或用户提供材料）
- `goal`：这封邮件要达成什么 + 约束（长度/语气/语言/禁区）

（可选但建议收集）`email_spec`：目前 API 不消费这个结构化字段；如果要影响生成，请把 one-ask/长度/禁区/合规等要求写进 `goal`（或放到 `template` 里）。

### C. 预期输出（Expected）
不要追求“逐字一致”，而是写“可验证的成功标准”：
- 找人：Top-K 里必须包含/排除哪些候选类型；每个候选必须给 evidence/sources/uncertainty。
- 邮件：必须有 Subject、必须引用哪些证据点、必须有一个清晰 ask、禁止虚构关系/经历、合规禁区。

## 3) 可直接复制的填写骨架

把下面这段复制到一个新 case 里，逐项填写（字段说明见 schema 与 rubric）：

```json
{
  "id": "fin_real_0001",
  "version": "0.1",
  "domain": "finance",
  "track": "TBD",
  "created_at": "YYYY-MM-DD",
  "source": {
    "type": "survey",
    "source_id": "TBD",
    "notes": "可选：样本背景/边界"
  },
  "input": {
    "find_recommendations_request": {
      "purpose": "Coffee Chat",
      "field": "Finance",
      "sender_profile": {
        "raw_text": "可选：一句话总结（已匿名）",
        "education": [],
        "experiences": [],
        "skills": [],
        "projects": []
      },
      "preferences": {
        "track": "Finance",
        "search_intent": "你要找什么人（角色/机构/方向）",
        "target_role_titles": ["Analyst", "Associate"],
        "seniority": "Analyst or Associate",
        "org_type": "Investment Bank / PE / VC / AM / Fintech ...",
        "bank_tier": "BB|EB|MM|Regional|Boutique|Unknown",
        "group": "（可选）Coverage/Product group，例如 TMT / M&A / LevFin",
        "group_type": "coverage|product|unknown",
        "sector": "（可选）行业，例如 TMT / Healthcare / FIG",
        "stage": "（可选）阶段，例如 Seed / Series A / Growth",
        "must_have": "关键词（用逗号分隔）",
        "must_not": "排除关键词（用逗号分隔）",
        "location": "地区/语言/时区",
        "contactability": "reply|prestige|balanced",
        "contact_channels": ["linkedin", "email"],
        "recruiting_context": {
          "role_type": "SA|FT|experienced|unknown",
          "timeline": "例如 next 2 weeks / Q1",
          "notes": "可选：补充背景"
        },
        "examples": "可选：理想样例",
        "evidence": "可选：用户提供的链接/摘录"
      }
    },
    "benchmark_context": {
      "notes": "可选：如果你用固定候选池，在这里放 candidate_pool"
    },
    "generate_email_request": {
      "sender": {
        "name": "Person A",
        "raw_text": "一句话背景（匿名）",
        "education": [],
        "experiences": [],
        "skills": [],
        "projects": [],
        "motivation": "动机",
        "ask": "一个明确请求"
      },
      "receiver": {
        "name": "Person B",
        "raw_text": "收件人公开信息摘录（匿名/可公开）",
        "education": [],
        "experiences": [],
        "skills": [],
        "projects": [],
        "context": "可选：为什么联系对方",
        "sources": ["https://..."],
        "evidence_snippets": [
          { "id": "e_r1", "text": "一条可公开引用的事实摘录", "url": "https://..." }
        ]
      },
      "goal": "邮件目标 + 约束（语言/长度/语气/禁区）",
      "template": null,
      "email_spec": {
        "output_language": "en|zh|mixed",
        "tone": "professional / friendly / concise ...",
        "max_words": 200,
        "max_chars": 200,
        "one_ask": {
          "type": "call|coffee_chat|intro|email_reply|other",
          "duration_minutes": 15,
          "timeframe": "next week",
          "time_windows": ["Tue 2-5pm ET"],
          "async_option": "可选：异步方案"
        },
        "value_offer": "你能提供的价值（1-2 句）",
        "hard_rules": ["禁止虚构关系/经历", "禁止提及未公开交易/客户"],
        "compliance_guardrails": {
          "forbid_investment_advice": true,
          "forbid_return_promises": true,
          "forbid_insider_info": true,
          "forbid_mentioning_unpublished_deals": true
        },
        "must_cite_evidence": true
      }
    }
  },
  "expected": {
    "find_recommendations": {
      "k": 10,
      "must_include_candidate_ids": [],
      "must_exclude_candidate_ids": [],
      "notes": "建议写成可验证标准，不要只写主观感受"
    },
    "generate_email": {
      "reference": {
        "subject": "（可选）一条参考 subject",
        "body_lines": [
          "（可选）一封你认为满意的参考邮件"
        ]
      },
      "assertions": {
        "language": "en|zh",
        "max_words": 200,
        "max_chars": 200,
        "must_include_phrases": [],
        "forbidden_phrases": [],
        "required_elements": [
          "subject_line",
          "why_them",
          "value",
          "clear_ask",
          "opt_out"
        ],
        "compliance": {
          "forbid_investment_advice": true,
          "forbid_return_promises": true,
          "forbid_insider_info": true,
          "forbid_mentioning_unpublished_deals": true
        }
      }
    }
  }
}
```
