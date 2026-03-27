---
name: modular_decomposition
trigger: always_on
description: "專案模組拆解原則：何時抽離、抽到哪、personal 如何援引、如何交付。"
---

# 模組拆解原則 (Modular Decomposition)

## 核心判斷：這段邏輯屬於誰？

對每個模組問三個問題：

1. **是否只服務這個專案？** → 留在 personal
2. **是否有其他專案可能需要相同能力？** → 抽到對應組別
3. **是否是這個專案對通用能力的特定配置？** → 留在 personal，但以 skill 援引組別模組

## 抽離方向：按職責對應組別

| 職責 | 目標組別 |
|------|----------|
| 爬蟲、外部資料取得 | `intelligence/` |
| AI 生成、媒體製作 | `creation/` |
| 摘要、教材、報告設計 | `education/` |
| 定期執行、排程 | `operations/` |
| 環境、硬體、基礎建設 | `infrastructure/` |

## Personal 專案的角色：薄消費者

抽離後，personal 專案應該是**薄的消費者**，不複製邏輯：

- 保留：專案特定的配置、資料、輸入輸出
- 移除：可被複用的功能邏輯
- 取代方式：在 `.agent/skills/` 寫一份 **援引技能（reference skill）**，說明如何呼叫組別模組

### 援引技能範本

```markdown
---
name: use-<module>
description: "如何從本專案呼叫 <group>/<module>"
---

# 呼叫 <module>

模組位置：`/data/logos/<group>/<module>/`

## 使用方式
<執行指令、參數說明、輸入輸出格式>

## 本專案的配置
<說明本專案傳入的特定參數或資料路徑>
```

## 拆解時不要過度抽象

- **不要**因為「未來可能用到」就抽離
- **要**當同一邏輯出現在 2 個以上的專案時才抽離
- 拆解前先文件化設計，再動程式碼

## 交付設計（Delivery）

當模組被抽離至 monorepo 後，若需要打包給外部使用：

1. **路徑引用**（內部使用）：personal 專案直接引用 `/data/logos/<group>/<module>/`，適合工作站環境
2. **Build 複製**（交付外部）：delivery 組負責建立 `build.sh`，將依賴的組別模組複製至獨立 package
3. **套件化**（長期）：成熟模組可發布為獨立 pip/npm 套件，personal 改為 `pip install` 引用

選擇原則：
- 僅自用 → 路徑引用
- 給熟悉 monorepo 的人 → 路徑引用 + 說明
- 給外部 / 獨立部署 → Build 複製或套件化

## 排程與核心行為分離

任何模組若有「可排程執行」的能力，**必須**把核心行為與排程觸發分開：

- **核心**：純函式或腳本，可直接呼叫，不依賴排程框架
- **排程 adapter**：薄包裝，呼叫核心並符合 `operations/scheduling` 的 manifest 格式

這樣在排程之外（測試、手動觸發、其他 agent 呼叫）也能直接使用核心行為。
