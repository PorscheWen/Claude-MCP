---
name: Git 自動 Commit 並 Push
description: 每次 commit 後自動 push，不需使用者另外確認
type: feedback
originSessionId: 18e1e710-daad-4079-94b8-f31c43a04774
---
每次 commit 之後，直接自動執行 git push，不需詢問使用者。

**Why:** 使用者明確指示「未來都自動 push」，省去每次確認的步驟。

**How to apply:** commit 完成後立即 push。若 push 失敗（如遠端有新 commit），先 pull --rebase 再 push，全程自動處理，不需停下來詢問。
