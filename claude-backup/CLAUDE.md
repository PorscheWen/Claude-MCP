# User Preferences

## 語言
- 預設使用**繁體中文**回應
- 必要時可切換英文

## 回答風格
- 完整、準確、結構清晰
- 語氣友善、自然、人性化
- 格式使用 **Markdown**
- 不加多餘的 emoji，除非明確要求

## 常見需求
- 摘要與文件整理
- 將複雜規範轉換為簡單易懂的摘要
- 延伸或推進對話內容

## 指令習慣
- 使用者常以「幫我…」開頭發出指令
- 回答可作為另一個 AI 助理的輸入素材

## 其他
- 使用者位於台灣新竹市東區
- 互動時段多為深夜或凌晨

---

# 工具與環境設定

> 所有 Token / Key 統一存放於 `C:\Users\BaoGo\Documents\ClaudeCode\.env`
> 每次新增或更換工具憑證，請同步更新此區塊與 `.env`

## Notion
- **用途**：儲存薪資明細、個人資料整理
- **Token**：`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`
- **薪資頁面 ID**：`33ffaa77d38680ffb092f956c667f599`
- **薪資資料庫 ID**：`33ffaa77-d386-81e3-9d95-c3f4b01383c2`
- **API 版本**：`2022-06-28`

## LINE Messaging API — What_To_Eat Bot
- **用途**：午餐推薦 LINE Bot
- **Channel ID**：`2008240021`
- **Bot ID**：`@921ylmxm`
- **Channel Secret**：`cb3dd7e663b69b0a202c181e3d07d99b`
- **Access Token**：`5/JDcR5pKjUztLLw9gsGV8EuWCIePY5SIF9nSUJRTa780M9fmFUpWEQs9iYsNYN85nkLvxKu9rOno3a4GrHFVCyYCWAVCCIZFZGXyrb5w0nFSB/5RoGzQ1Yi+Na6rNpBT0J8fbO0DjDPEGHxTV06jgdB04t89/1O/w1cDnyilFU=`
- **User ID**：`Uc4b6168aaeef9ffdf18e4ab0273ff9b9`
- **Webhook URL (n8n)**：`https://baogo.app.n8n.cloud/webhook-test/f97a8e90-df0b-444d-9feb-5e3c495d4888`
- ⚠️ Access Token 建議定期更換

## LINE Messaging API — Memo Bot
- **用途**：個性化管家 LINE Bot（聊天、喜好記錄、節日提醒）
- **Channel ID**：`2009774986`
- **Channel Secret**：`94b0323bd3947b694bdc9b493ab3c35e`
- **Access Token**：`/Gd7zCXMLFju7lbGiKJwV1l8Xwt3M8s1vhpRJ0LeGzHbJ7hdsXFr2prZG9sakfDVcLl6mLRdLYyx6eixHAsGAOIDQT35Q9cUzXH2c04qWNqsawxYaBPdr/fSeLCwPiRRtu84529qVdxMRyZwL7s6wwdB04t89/1O/w1cDnyilFU=`
- **Notion 喜好 DB**：`03379f2a060847eaae6a7f6682d4a4dc`
- **Notion 重要日期 DB**：`e9845c76ea754920a2a827264ebef5b3`
- **Repo**：`PorscheWen/Bot_Agent`
- ⚠️ Access Token 建議定期更換

## Google Drive / Gmail (MCP: google-workspace)
- **用途**：搜尋 Gmail 信件、上傳/下載 Drive 檔案
- **薪資單資料夾**：`/薪資單`
- **連線方式**：透過 MCP `google-workspace` 工具，已整合於 Claude Code

## stock-advisor 自選股清單
- **台股（個股）**：2330（台積電）、2542（興富發）、2618（長榮航）、2801（彰銀）、2812（台中銀）、2880（華南金）、2884（玉山金）、5880（合庫金）、9945（潤泰新）、1432（大魯閣）
- **台股（ETF）**：00631L（元大台灣50正2）、00712（復華富時不動產）、009816（凱基台灣TOP50）
- **資料來源**：2026/04/11 即時未實現損益截圖，共13筆，總市值約 4,237,544 TWD，未實現損益 +233,781
- **美股**：NVDA、AAPL、MSFT、TSLA、AMD

## 其他
- **PDF 解密密碼**：`H122407592`（身分證字號，用於解開薪資單 PDF）
