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
