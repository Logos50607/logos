---
name: discipline-evolution
trigger: model_decision
description: "新增、修改或強制執行 disciplines 時必讀：三層執行架構（條文／機制／稽核）與制度升級迴圈（診斷→立法→機制化→驗證→記錄→觀察）。"
---

# 制度演進規範 (Discipline Evolution)

## 三層執行架構

任何行為規範的效力來自三層，設計時必須明確它落在哪幾層：

| 層 | 載體 | 特性 |
|----|------|------|
| **條文** | discipline 文本（注入 context） | 涵蓋面廣、能表達原則與理由；但會衰減——規則越多，單條遵守率越低 |
| **機制** | hook、sync 過濾、測試、CI、權限層 | 不可繞過；但只能強制「可機器判定」的行為 |
| **稽核** | git log、AGENT_PLAN、決策紀錄 | 事後可追溯，支撐覆核與修正 |

核心原則：**可機器判定的行為必須做成機制，條文只保留原則與理由**（discipline_metadata §3）。條文層失守時機制要接得住；兩層都管不到的，靠稽核留痕。三層各自獨立驗證：條文靠 agent 讀後行為、機制靠測試與實測、稽核靠紀錄存在。

## 制度升級迴圈

觸發時機：使用者糾正、agent 違規、重複摩擦、或發現某規範只存在條文層。

```
1. 診斷    定位產生問題的制度缺口，不是只修當次產出（agent_behavior §1）
2. 立法    先改 discipline 文本（doc_before_impl），commit
3. 機制化  能強制的做成 hook／腳本／過濾；同目錄寫 test_ 前綴測試並執行通過
4. 驗證    端到端實測機制生效——不以「腳本跑完不報錯」為準
           （如 hooks 需以新 session 實測；post_deploy_verify 精神）
5. 記錄    決策紀錄入 reports/discipline-proposals/，AGENT_PLAN 標注執行與驗證，
           執行 sync 同步至各 agent
6. 觀察    留一條觀察待辦；訊號出現時回到步驟 1
```

## 分級調整信號（步驟 6 所觀察的對象）

| 訊號 | 動作 |
|------|------|
| model_decision 規則常被漏讀 | 升 always_on，或直接機制化 |
| always_on 規則與多數 session 無關 | 降 model_decision（description 必須寫明何時必讀） |
| 條文屢次失守且行為可機器判定 | 機制化（hook／過濾／CI） |
| 機制誤攔率高 | 收窄機器判定條件，原則退回條文層 |

## 禁止行為

- 新增條文時不問「這能不能做成機制」
- 機制未經測試＋端到端實測就宣告生效
- 升級完成後不留決策紀錄與觀察待辦（沒有步驟 5、6 的升級視為未完成）
