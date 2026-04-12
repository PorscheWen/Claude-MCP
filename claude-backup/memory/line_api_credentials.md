---
name: LINE API 憑證
description: BaoGo 的 LINE Messaging API 連線資訊，用於發送訊息到個人或群組
type: reference
originSessionId: 0e500c2d-6b0b-4afb-94d3-78cfa6de134c
---
## LINE Messaging API

- **Channel ID**: 2008240021
- **Channel Secret**: cb3dd7e663b69b0a202c181e3d07d99b
- **Channel Access Token**: 5/JDcR5pKjUztLLw9gsGV8EuWCIePY5SIF9nSUJRTa780M9fmFUpWEQs9iYsNYN85nkLvxKu9rOno3a4GrHFVCyYCWAVCCIZFZGXyrb5w0nFSB/5RoGzQ1Yi+Na6rNpBT0J8fbO0DjDPEGHxTV06jgdB04t89/1O/w1cDnyilFU=
- **User ID**: Uc4b6168aaeef9ffdf18e4ab0273ff9b9
- **Webhook URL (n8n)**: https://baogo.app.n8n.cloud/webhook-test/f97a8e90-df0b-444d-9feb-5e3c495d4888

## 發送訊息指令

```bash
curl -X POST https://api.line.me/v2/bot/message/push \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {Channel Access Token}" \
  -d @message.json
```

## 注意事項
- Access Token 在對話中曝光過，建議更換新的
- Group ID 尚未取得（需 Bot 加入群組後從 Webhook 取得）
