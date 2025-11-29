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
