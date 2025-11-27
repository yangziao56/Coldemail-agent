# Honest Connect Email Agent (v0)

命令行小工具：读取 `sender.json`、`receiver.json` 和一个目标字符串，调用 OpenAI API 生成一封真诚的第一封冷邮件（包含 Subject + Body）。

## 准备工作
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 设置 OpenAI API Key：
   ```bash
   export OPENAI_API_KEY=your_api_key
   ```

## 输入格式
- `sender.json`
  ```json
  {
    "name": "Your Name",
    "raw_text": "在这里粘贴你的简历 / 自我介绍 / 代表性项目描述。",
    "motivation": "用你自己的话写：为什么想联系这个人，对他/她哪点很感兴趣。",
    "ask": "你希望对方帮什么，比如：a 20-min Zoom call about X / feedback on Y / career advice on Z."
  }
  ```
- `receiver.json`
  ```json
  {
    "name": "Receiver Name",
    "raw_text": "在这里粘贴对方的个人简介 / 代表性工作介绍。",
    "context": "你对这个人或项目的了解，比如最近的动态或共同话题。"
  }
  ```

示例文件在 `examples/` 目录下。

## 使用方法
```bash
python -m src.cli \
  --sender examples/sender.json \
  --receiver examples/receiver.json \
  --goal "希望邀请对方聊 20 分钟，讨论他最近的项目和你的相关经验" \
  --model gpt-4o-mini
```

命令会将生成的邮件文本输出到终端，可直接复制粘贴到邮箱客户端。

### 用简历直接生成 sender/receiver profile
如果不想手写 `sender.json` / `receiver.json`，可以把自己的简历或对方的公开简介保存成纯文本，交给命令行自动生成 profile：

```bash
python -m src.cli \
  --sender-resume /path/to/my_resume.txt \
  --sender-ask "希望邀请对方帮忙点评我的开源项目" \
  --receiver-resume /path/to/their_profile.txt \
  --receiver-context "我们都在做LLM agent相关项目" \
  --goal "请对方约个20分钟视频通话" \
  --sender-output examples/generated_sender.json \
  --receiver-output examples/generated_receiver.json
```

- `--sender-resume` / `--receiver-resume`：从纯文本简历/简介里提取 `name` + `raw_text`，并让 LLM 自动补全（或改写）必要字段。
- `--sender-ask` / `--sender-motivation` / `--receiver-context`：可选覆盖字段，避免模型乱猜。
- `--sender-output` / `--receiver-output`：把生成的 JSON 落盘，便于下次重复使用。
