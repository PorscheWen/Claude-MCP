#!/usr/bin/env python3
"""
Claude CLI - 在終端機中與 Claude 對話
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

# 固定不變的 system prompt，適合快取
SYSTEM_PROMPT = """你是一位友善、專業的 AI 助理。你的特點：

1. 使用繁體中文回答，除非使用者要求其他語言
2. 回答簡潔清晰，必要時提供範例
3. 對程式碼問題，優先提供可執行的範例
4. 誠實說明不確定的地方，不捏造資訊
5. 保持對話脈絡，記住使用者在本次對話中提到的重要資訊

你擅長的領域包括：程式設計、資料分析、寫作潤飾、問題分析與解決。
"""

def main():
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key or api_key.startswith("sk-ant-api03-YOUR"):
        print("請先在 .env 中設置有效的 ANTHROPIC_API_KEY")
        print("從 https://console.anthropic.com/ 取得 API key")
        return

    client = Anthropic(api_key=api_key)

    print("Claude CLI 已啟動 (輸入 'exit' 或 'quit' 離開)")
    print("=" * 60)

    conversation_history = []

    while True:
        try:
            user_input = input("\n你: ").strip()

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n再見！")
                break

            if not user_input:
                continue

            conversation_history.append({
                "role": "user",
                "content": user_input
            })

            print("\nClaude: ", end="", flush=True)

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}  # 快取 system prompt
                }],
                messages=conversation_history
            )

            assistant_message = response.content[0].text
            print(assistant_message)

            # 顯示快取使用狀況
            usage = response.usage
            cache_read = getattr(usage, "cache_read_input_tokens", 0)
            cache_write = getattr(usage, "cache_creation_input_tokens", 0)
            if cache_read or cache_write:
                print(f"\n[快取: 寫入 {cache_write} / 命中 {cache_read} tokens]", end="")

            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

        except KeyboardInterrupt:
            print("\n\n再見！")
            break
        except Exception as e:
            print(f"\n錯誤: {e}")

if __name__ == "__main__":
    main()
