"""
schema.py - Switchboard 統一訊息資料模型

所有 channel processor 輸出皆轉換為 Message，
上層（output/core）只依賴此 schema，不感知平台細節。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    id: str                         # 平台原生 message ID
    channel: str                    # 來源 channel，如 "line_personal"
    chat_id: str                    # 聊天室 / 群組 ID
    sender_id: str                  # 發送者 ID
    text: str                       # 訊息文字
    ts: float                       # Unix timestamp（秒）
    sender_name: Optional[str] = None
    raw: dict = field(default_factory=dict)   # 原始 payload，供 debug 用
