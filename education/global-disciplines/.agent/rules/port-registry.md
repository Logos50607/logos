---
name: port-registry
trigger: model_decision
description: "起任何服務前必須查 port 清單、避免衝突，並在 internal-control/ports.json 登記。"
---

# Port 使用規範

## 核心規則

**起任何服務（server、DB、proxy、worker）前，必須：**

1. 確認 port 沒被佔用：`ss -tlnp | grep :<port>`
2. 查 `/data/logos/internal-control/ports.json` 確認沒有其他服務登記同一 port
3. 起服務後，在 `ports.json` 補登記

## Port 清單位置

```
/data/logos/internal-control/ports.json
```

格式：
```json
{
  "port": 15432,
  "service": "mogroup-switchboard-db",
  "description": "mogroup-switchboard PostgreSQL",
  "owner": "urfit-tech/mogroup-switchboard",
  "host": "localhost"
}
```

## 挑 Port 的原則

- **不用熱門 port**（5432、5433、8080、8000、3000、6379 等已常被佔用）
- 偏移規則：以服務的標準 port 為基礎加 10000（例：PostgreSQL 5432 → 15432，FastAPI 8000 → 18000）
- 挑完先 `ss -tlnp | grep :<port>` 確認再寫進 compose / .env

## 禁止行為

- 直接用 5432 / 8080 等熱門 port 而不先確認
- 起服務後不在 `ports.json` 登記
