#!/usr/bin/env python3
"""
Claude API 基本使用示例
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

def main():
    # 載入 .env 文件中的環境變數
    load_dotenv()

    # 從環境變數讀取 API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ 錯誤: 請設置 ANTHROPIC_API_KEY 環境變數")
        print("\n📝 步驟:")
        print("1. 複製 .env.example 為 .env: cp .env.example .env")
        print("2. 在 .env 中填入您的 API key")
        print("3. 從 https://console.anthropic.com/ 獲取 API key")
        return

    # 初始化 Claude 客戶端
    client = Anthropic(api_key=api_key)

    # 發送訊息給 Claude
    print("🤖 正在與 Claude 對話...")
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",  # 使用最新的 Claude 3.5 Sonnet 模型
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "你好！請用繁體中文簡單介紹一下你自己。"
            }
        ]
    )

    # 輸出回應
    print("\n" + "=" * 60)
    print("💬 Claude 的回應:")
    print("=" * 60)
    print(message.content[0].text)
    print("=" * 60)
    print(f"\n📊 使用的 tokens: {message.usage.input_tokens} (輸入) + {message.usage.output_tokens} (輸出)")

if __name__ == "__main__":
    main()
