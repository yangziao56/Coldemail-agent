# notes.md — Honest Connect Email Agent

## 0. 我要做的东西（一句话）

从两个人身上尽可能多的信息里，  
找到他们的**交集**和**可以互相提供的价值**，  
写出一封**真诚的第一封冷邮件**，帮他们建立真实的连接。

之后再在这个核心上扩展到：
- 一对多（同一个 sender → 多个 receiver）
- 自动帮用户找合适的 receiver
- 不同场景：fund / tech / 学生找老师 / 职场前辈等

---

## 1. 核心抽象（以后都尽量不改）

整个项目围绕一个核心函数：

> `(SenderProfile, ReceiverProfile, Goal) -> One sincere email`

- **SenderProfile**：关于发送者的一切有用信息  
- **ReceiverProfile**：关于接收者的一切可获得的信息  
- **Goal**：这封信要达到的目的（例如约 20 分钟电话 / 请教问题 / 求建议）

无论是：
- 投行新人 → 创业者 / 前辈  
- 工程师 → big tech mentor  
- 学生 → 教授  

都要能被抽象成这三样输入。如果某个未来功能完全塞不进这个抽象，就先不做。

---

## 2. v0 版本：只做一件非常小但真实的事

### 2.1 v0 目标

做一个**命令行小工具**：

- 输入：
  - 一个 `sender.json`
  - 一个 `receiver.json`
  - 一个简单的 `goal` 字符串
- 输出：
  - 一封可以直接复制进邮箱的邮件文本（含 Subject）

暂时不管 UI、不管自动找人、不管批量发，只追求一封邮件的质量和“真诚感”。

### 2.2 v0 输入格式（先用最简单可用的）

`sender.json`（用户自己写，越详细越好）：

```json
{
  "name": "Your Name",
  "raw_text": "在这里粘贴你的简历 / 自我介绍 / 代表性项目描述。",
  "motivation": "用你自己的话写：为什么想联系这个人，对他/她哪点很感兴趣。",
  "ask": "你希望对方帮什么，比如：a 20-min Zoom call about X / feedback on Y / career advice on Z."
}
