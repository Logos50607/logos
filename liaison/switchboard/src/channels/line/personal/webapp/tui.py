# /// script
# dependencies = ["textual", "playwright", "cryptography"]
# ///
"""
tui.py - LINE 個人帳號 Terminal UI

用法: uv run tui.py
操作:
  ↑↓       切換聊天室          n    新對話（聯絡人/群組）
  Enter    開啟聊天 / 選擇回覆  r    重新整理
  Tab      聊天清單 ↔ 輸入框   q    離開
  m        對話區（可上下捲）  [    載入更早訊息
  d        收回自己的訊息      Escape  取消回覆 / 回清單
"""

# 目錄:
# 1. 常數 & 輔助函式
# 2. MessageItem widget（對話氣泡，可選取回覆 / 收回）
# 3. ChatItem widget
# 4. ContactPickerScreen modal
# 5. TuiApp：compose / on_mount / 事件處理
# 6. TuiApp：非同步任務 (cdp / preload / send / poll / contacts / refresh / unsend)
# 7. TuiApp：渲染 (rebuild_list / show_messages / append_message)

import ast, json, sys, time
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

ROOT   = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

_DATA    = ROOT / "data"
_DATA.mkdir(exist_ok=True)
_MSGS    = _DATA / "messages.json"
_FRIENDS = _DATA / "friends.json"
_GROUPS  = _DATA / "groups.json"
_LOG     = _DATA / "tui.log"

import traceback as _traceback

def _log_exc(tag: str) -> None:
    """將當前例外的完整 traceback 附加到 tui.log。"""
    with _LOG.open("a") as f:
        f.write(f"\n[{datetime.now()}] {tag}\n")
        _traceback.print_exc(file=f)

# 不同發話者的文字顏色（依 mid hash 循環）
_SENDER_PALETTE = [
    "bright_cyan", "bright_yellow", "bright_magenta",
    "bright_green", "bright_blue", "orange1",
    "chartreuse3", "deep_sky_blue1", "hot_pink",
]

def _sender_style(mid: str) -> str:
    return _SENDER_PALETTE[hash(mid) % len(_SENDER_PALETTE)]

_CT = {
    0:  "",
    1:  "📷 圖片",
    2:  "🎬 影片",
    3:  "🎵 音訊",
    7:  "🔖 貼圖",
    13: "📇 聯絡人名片",
    14: "📎 檔案",
    15: "📍 位置",
    18: "🔔 系統通知",
    22: "🤖 Flex Message",
}

_LOC_KEY = {
    "C_MI": "加入群組",
    "C_ML": "離開群組",
    "C_PN": "釘選訊息",
    "C_MK": "踢出成員",
    "C_NC": "群組改名",
}


# ── 1. 輔助 ───────────────────────────────────────────────────────

def _ts(ms) -> str:
    try:    return datetime.fromtimestamp(int(ms) / 1000).strftime("%H:%M")
    except: return ""

def _meta(m: dict) -> dict:
    v = m.get("contentMetadata", {})
    if isinstance(v, str):
        try:    return ast.literal_eval(v)
        except: return {}
    return v or {}

def _preview(m: dict) -> str:
    ct = int(m.get("contentType", 0))
    if ct == 0:  return str(m.get("text") or "")[:40]
    if ct == 14: return f"📎 {_meta(m).get('FILE_NAME', '檔案')}"
    if ct == 18:
        loc = _meta(m).get("LOC_KEY", "")
        return f"🔔 {_LOC_KEY.get(loc, loc or '系統通知')}"
    if ct == 22:
        try:
            import json as _j
            flex = _j.loads(_meta(m).get("FLEX_JSON", "{}"))
            alt = flex.get("altText") or ""
            return f"🤖 {alt[:35]}" if alt else "🤖 Flex Message"
        except Exception:
            return "🤖 Flex Message"
    dur = _meta(m).get("DURATION")
    if dur:      return f"{_CT.get(ct,'?')} ({int(dur)//1000}s)"
    return _CT.get(ct, f"[type {ct}]")

def _migrate_legacy() -> None:
    """將舊路徑的資料搬移到 data/ 目錄（一次性）。"""
    old_msgs = ROOT / "messages.json"
    if old_msgs.exists() and not _MSGS.exists():
        old_msgs.rename(_MSGS)
    old_contacts = Path(__file__).parent / "contacts.json"
    if old_contacts.exists() and not _FRIENDS.exists() and not _GROUPS.exists():
        existing = json.loads(old_contacts.read_text())
        friends = {m: n for m, n in existing.items() if m.startswith("U")}
        groups  = {m: n for m, n in existing.items()
                   if m.startswith("C") or m.startswith("R")}
        _FRIENDS.write_text(json.dumps(friends, ensure_ascii=False, indent=2))
        _GROUPS.write_text(json.dumps(groups,   ensure_ascii=False, indent=2))


def _load_contacts() -> dict:
    contacts = {}
    for p in (_FRIENDS, _GROUPS):
        if p.exists():
            contacts.update(json.loads(p.read_text()))
    return contacts


def _save_contacts(friends: dict, groups: dict) -> None:
    _FRIENDS.write_text(json.dumps(friends, ensure_ascii=False, indent=2))
    _GROUPS.write_text(json.dumps(groups, ensure_ascii=False, indent=2))

def _load_messages() -> dict:
    return json.loads(_MSGS.read_text()) if _MSGS.exists() else {}

def _save_messages(data: dict) -> None:
    """背景執行寫檔，避免大型 JSON 擋住 event loop。"""
    import threading
    content = json.dumps(data, ensure_ascii=False, indent=2)
    threading.Thread(target=lambda: _MSGS.write_text(content), daemon=True).start()


# ── 2. MessageItem ────────────────────────────────────────────────

class MessageItem(ListItem):
    """對話氣泡：可選取（Enter 回覆，d 收回自己的）。"""

    def __init__(self, msg: dict, my_mid: str | None, contacts: dict):
        super().__init__()
        self._msg      = msg
        self._my_mid   = my_mid
        self._contacts = contacts

    @property
    def msg_id(self) -> str:
        return self._msg.get("id", "")

    @property
    def is_mine(self) -> bool:
        return bool(self._my_mid and self._msg.get("from") == self._my_mid)

    def _build_text(self) -> str:
        ct       = int(self._msg.get("contentType", 0))
        raw_text = self._msg.get("text") or ""
        if ct != 0:
            return _preview(self._msg)
        if raw_text:
            return str(raw_text)
        if self._msg.get("chunks"):
            if self.is_mine:
                return "[已發送]"
            return "🔐 [E2EE]"
        return ""

    def compose(self) -> ComposeResult:
        text       = self._build_text()
        ts         = _ts(self._msg.get("createdTime", 0))
        sender_mid = self._msg.get("from", "")
        if self.is_mine:
            bubble = Text.assemble(
                (" ", ""), (f" {text} ", "black on green"),
                (" ", ""), ("  ", ""), (ts, "dim"),
            )
            yield Static(Align.right(bubble))
        else:
            color  = _sender_style(sender_mid)
            sender = self._contacts.get(sender_mid, "")
            bg     = f"black on {color}"
            parts: list = []
            if sender:
                parts.append((f" {sender} ", f"bold {bg}"))
                parts.append(("\n", ""))
            parts += [(" ", ""), (f" {text} ", bg), (" ", ""), ("  ", ""), (ts, "dim")]
            yield Static(Text.assemble(*parts))


# ── 3. ChatItem ───────────────────────────────────────────────────

class ChatItem(ListItem):
    def __init__(self, mid: str, label: str, preview: str, unread: int = 0):
        super().__init__()
        self.mid     = mid
        self.label   = label
        self.preview = preview
        self.unread  = unread

    def compose(self) -> ComposeResult:
        badge = f" [bold red]({self.unread})[/]" if self.unread else ""
        yield Label(f"[bold]{self.label}[/]{badge}", markup=True)
        yield Label(f"[dim]{self.preview}[/]",       markup=True)


# ── 3. ContactPickerScreen ────────────────────────────────────────

class ContactPickerScreen(ModalScreen):
    """按 n 開啟；上下選擇，Enter 確認，Esc 關閉。"""
    BINDINGS = [Binding("escape", "dismiss", "關閉")]
    CSS = """
    ContactPickerScreen { align: center middle; }
    #picker-box {
        width: 52; height: 22;
        border: double $primary;
        background: $surface;
        padding: 1 2;
    }
    #picker-list { height: 1fr; margin-top: 1; }
    """

    def __init__(self, contacts: dict, known_mids):
        super().__init__()
        seen, self._all = set(), []
        for mid, name in sorted(contacts.items(), key=lambda x: x[1].lower()):
            icon = "👥 " if mid.startswith("C") else "🙍 "
            self._all.append((mid, f"{icon}{name}"))
            seen.add(mid)
        for mid in known_mids:
            if mid not in seen:
                icon = "👥 " if mid.startswith("C") else "🙍 "
                self._all.append((mid, f"{icon}{mid[:22]}…"))

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-box"):
            yield Label("[bold]開啟對話[/bold]  [dim](輸入篩選)[/dim]", markup=True)
            yield Input(placeholder="搜尋聯絡人 / 群組…", id="picker-search")
            yield ListView(id="picker-list")

    def on_mount(self) -> None:
        self._fill_list(self._all)
        self.query_one("#picker-search", Input).focus()

    def on_input_changed(self, ev: Input.Changed) -> None:
        q = ev.value.lower()
        self._fill_list([(m, d) for m, d in self._all
                         if q in d.lower() or q in m.lower()])

    def _fill_list(self, items) -> None:
        lv = self.query_one("#picker-list", ListView)
        lv.clear()
        for mid, display in items:
            li = ListItem(Label(display, markup=False))
            li._pick_mid = mid
            lv.append(li)

    def on_list_view_selected(self, ev: ListView.Selected) -> None:
        self.dismiss(getattr(ev.item, "_pick_mid", None))


# ── 4. App ────────────────────────────────────────────────────────

CSS = """
Screen { layout: vertical; }
#body  { height: 1fr; }
#sidebar { width: 26; border-right: solid $primary-darken-2; }
#sidebar Label { padding: 0 1; }
#messages { height: 1fr; }
#reply-bar { height: 1; background: $primary-darken-2; padding: 0 1; display: none; }
#input-row { height: 3; dock: bottom; }
#input { width: 1fr; }
ChatItem { height: 4; padding: 0 1; }
ChatItem.--highlight { background: $primary-darken-1; }
MessageItem { height: auto; padding: 0 1; }
MessageItem > Static { width: 1fr; }
"""

class TuiApp(App):
    CSS = CSS
    BINDINGS = [
        Binding("q",      "quit",          "離開"),
        Binding("n",      "new_chat",      "新對話"),
        Binding("r",      "refresh",       "重新整理"),
        Binding("[",      "load_older",    "載入更早"),
        Binding("m",      "focus_messages","對話區"),
        Binding("d",      "unsend",        "收回", show=False),
        Binding("escape", "focus_list",    "聊天清單"),
        Binding("tab",    "focus_input",   "輸入框", show=False),
    ]
    current_chat: reactive[str | None] = reactive(None)

    _SIDEBAR_PAGE = 30   # 每次載入幾筆

    def __init__(self):
        super().__init__()
        self._data:          dict           = {}
        self._contacts:      dict           = {}
        self._my_mid:        str | None     = None
        self._page                          = None
        self._connected:     bool           = False
        self._order:         list[str]      = []
        self._unread:        dict[str, set] = {}
        self._token:         str | None     = None
        self._token_ts:      float          = 0.0
        self._pw                            = None
        self._browser                       = None
        self._sidebar_chats: list           = []   # 完整排序後的 (mid, ts) 清單
        self._sidebar_shown: int            = 0    # 已顯示幾筆
        self._chat_shown:    dict[str, int] = {}   # 各聊天室目前顯示幾則
        self._reply_to:      dict | None    = None  # 目前選取要回覆的訊息
        self._ltsm_cache:    dict           = {}    # {receiver_key_id: my_ltsm_id}
        self._chan_cache:    dict           = {}    # {(my_ltsm_id, sender_mid): channel_id}
        self._pub_cache:     dict           = {}    # {sender_mid: pub_b64}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label("[b] 聊天室[/]", markup=True)
                yield ListView(id="chat-list")
            with Vertical(id="main"):
                yield ListView(id="messages")
                yield Label("", id="reply-bar", markup=False)
                with Horizontal(id="input-row"):
                    yield Input(placeholder="輸入訊息… [Enter 送出]", id="input")
        yield Footer()

    def on_mount(self) -> None:
        self.title     = "LINE Personal"
        self.sub_title = "連線中…"
        with _LOG.open("a") as f:
            f.write(f"\n[{datetime.now()}] ── TUI 啟動 ──\n")
        _migrate_legacy()
        self._data     = _load_messages()
        self._contacts = _load_contacts()
        self._rebuild_list()
        self.run_worker(self._connect_cdp(), exclusive=True, name="cdp")
        self.set_interval(10, self._poll)

    # ── 事件處理 ─────────────────────────────────────────────────

    def on_list_view_selected(self, ev: ListView.Selected) -> None:
        item = ev.item
        if isinstance(item, ChatItem):
            self.current_chat = item.mid
            self._unread.pop(item.mid, None)
            self._show_messages(item.mid)
            self.query_one("#input", Input).focus()
            if self._connected:
                self.run_worker(self._decrypt_chat(item.mid), name="decrypt")
        elif isinstance(item, MessageItem):
            self._reply_to = item._msg
            preview = str(item._msg.get("text", _preview(item._msg)))[:50]
            bar = self.query_one("#reply-bar", Label)
            bar.update(f"↩ 回覆: {preview}")
            bar.display = True
            self.query_one("#input", Input).focus()

    async def on_input_submitted(self, ev: Input.Submitted) -> None:
        text = ev.value.strip()
        if not text or not self.current_chat:
            return
        ev.input.clear()
        if not self._connected:
            self.notify("尚未連線，請稍候", severity="warning"); return
        self.run_worker(self._send(self.current_chat, text), name="send")

    def action_focus_list(self) -> None:
        if self._reply_to is not None:
            self._reply_to = None
            bar = self.query_one("#reply-bar", Label)
            bar.update("")
            bar.display = False
            self.query_one("#input", Input).focus()
        else:
            self.query_one("#chat-list").focus()
    def action_focus_input(self)    -> None: self.query_one("#input").focus()
    def action_focus_messages(self) -> None: self.query_one("#messages").focus()

    def action_refresh(self) -> None:
        if self.current_chat:
            self.run_worker(self._refresh_chat(self.current_chat), name="refresh")

    def action_new_chat(self) -> None:
        self.push_screen(
            ContactPickerScreen(self._contacts, set(self._data.keys())),
            self._on_chat_picked,
        )

    def _on_chat_picked(self, mid: str | None) -> None:
        if not mid: return
        self._data.setdefault(mid, [])
        self.current_chat = mid
        self._rebuild_list()
        self._show_messages(mid)
        self.query_one("#input", Input).focus()
        if self._connected:
            self.run_worker(self._refresh_chat(mid), name="refresh-pick")

    def action_quit(self) -> None:
        """直接強制退出，kill 整個 process group（Python + uv 同時死，shell 立刻拿回 terminal）。"""
        import os, signal, termios
        with _LOG.open("a") as f:
            f.write(f"[{datetime.now()}] action_quit called\n")
        # 先送 escape sequence 還原 terminal 顯示
        try:
            os.write(1, b"\033[?1049l\033[?25h\033[0m\r\n")
        except Exception:
            pass
        # 還原 termios（echo + canonical mode）
        try:
            fd = os.open("/dev/tty", os.O_RDWR)
            attrs = termios.tcgetattr(fd)
            attrs[3] |= termios.ECHO | termios.ICANON
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            os.close(fd)
        except Exception:
            pass
        # Kill 整個 process group（含 uv），shell 立刻拿回 terminal
        os.killpg(os.getpgrp(), signal.SIGKILL)

    # ── 非同步任務 ───────────────────────────────────────────────

    async def _get_token(self) -> str:
        """快取 token，1 小時內重用，過期才 reload 重取。"""
        if self._token and time.time() - self._token_ts < 3600:
            return self._token
        from gw_client import get_access_token
        self._token    = await get_access_token(self._page)
        self._token_ts = time.time()
        return self._token

    async def _connect_cdp(self) -> None:
        try:
            from playwright.async_api import async_playwright
            from gw_client import CDP_URL, find_ext_page
            from send_api import get_my_info
            self._pw      = await async_playwright().start()
            self._browser = await self._pw.chromium.connect_over_cdp(CDP_URL)
            self._page    = find_ext_page(self._browser.contexts[0])
            self._my_mid, _ = await get_my_info(self._page)
            self._connected  = True
            self.sub_title   = "已連線"
            self.notify("已連線到 LINE ✓")
            # 先同步聯絡人名稱，再開始預載（確保名稱已就緒）
            await self._sync_contacts()
            self.run_worker(self._preload_recent(), name="preload")
        except Exception as e:
            self.notify(f"連線失敗: {e}", severity="error")
            _log_exc("connect_cdp 失敗")

    async def _preload_recent(self) -> None:
        """用 getMessageBoxes 一次取得全部 active 聊天室及最後訊息。"""
        try:
            from fetch_messages import fetch_message_boxes
            token = await self._get_token()
            self.sub_title = "同步聊天室…"
            boxes = await fetch_message_boxes(self._page, token, last_msgs=30)
            new_count = 0
            for box in boxes:
                mid  = box["id"]
                msgs = box.get("lastMessages") or []
                if mid not in self._data:
                    new_count += 1
                if msgs:
                    # 用 id 去重後合併（新訊息優先，舊的不覆蓋）
                    existing = {m["id"]: m for m in self._data.get(mid, [])}
                    for m in msgs:
                        existing.setdefault(m["id"], m)
                    self._data[mid] = list(existing.values())
                else:
                    self._data.setdefault(mid, [])
            _save_messages(self._data)
            self._rebuild_list()
            self.sub_title = "已連線"
            if new_count:
                self.notify(f"新增 {new_count} 個聊天室 ✓")
        except Exception:
            self.sub_title = "已連線"
            _log_exc("preload 失敗")

    async def _send(self, mid: str, text: str) -> None:
        from send_api import send_e2ee_text
        reply_id = self._reply_to["id"] if self._reply_to else None
        result   = await send_e2ee_text(self._page, mid, text, reply_to_id=reply_id)
        if result.get("ok"):
            msg: dict = {"from": self._my_mid or "", "to": mid,
                         "contentType": 0, "text": text,
                         "createdTime": str(int(time.time() * 1000)),
                         "id": f"local-{result['seq']}"}
            if reply_id:
                msg["relatedMessageId"]    = reply_id
                msg["messageRelationType"] = 3
            # 清除回覆狀態
            self._reply_to = None
            bar = self.query_one("#reply-bar", Label)
            bar.update("")
            bar.display = False
            self._data.setdefault(mid, []).append(msg)
            _save_messages(self._data)
            if self.current_chat == mid:
                self._append_message(msg, mid)
        else:
            self.notify(f"發送失敗: {result.get('error')}", severity="error")

    async def _poll(self) -> None:
        if not self._connected: return
        self.run_worker(self._fetch_new(), name="poll")

    async def _fetch_new(self) -> None:
        """用 getMessageBoxes 篩出有新訊息的聊天室，再逐一抓完整更新。"""
        try:
            from fetch_messages import fetch_message_boxes, fetch_chat_messages
            token = await self._get_token()
            boxes = await fetch_message_boxes(self._page, token, last_msgs=1)

            # 找出 lastDeliveredMessageId 比本地最新訊息 id 還新的聊天室
            changed = False
            for box in boxes:
                mid = box["id"]
                box_last_id = (box.get("lastDeliveredMessageId") or {}).get("messageId")
                local_msgs  = self._data.get(mid, [])
                local_ids   = {m["id"] for m in local_msgs}
                if not box_last_id or box_last_id in local_ids:
                    continue
                known = {m["id"] for m in local_msgs}
                fresh = await fetch_chat_messages(self._page, token, mid, 10)
                new   = [m for m in fresh if m["id"] not in known]
                if not new: continue
                self._data.setdefault(mid, []).extend(new)
                self._unread.setdefault(mid, set()).update(m["id"] for m in new)
                changed = True
                print("\a", end="", flush=True)
                label = self._contacts.get(mid, mid[:12] + "…")
                self.notify(f"💬 {label}: {_preview(new[-1])}")
                self._rebuild_list()
                if self.current_chat == mid:
                    for m in sorted(new, key=lambda x: int(x.get("createdTime", 0))):
                        self._append_message(m, mid)
                # 若有 E2EE 訊息，背景解密
                if any(m.get("chunks") and m.get("text") is None for m in new):
                    self.run_worker(self._decrypt_chat(mid), name=f"decrypt-{mid}")
            if changed:
                _save_messages(self._data)
        except Exception:
            _log_exc("fetch_new 失敗")

    async def _sync_contacts(self) -> None:
        try:
            from fetch_contacts import fetch_contacts
            self.sub_title = "同步聯絡人…"
            new = await fetch_contacts(self._page, await self._get_token())
            if new:
                self._contacts.update(new)
                friends = {m: n for m, n in self._contacts.items() if m.startswith("U")}
                groups  = {m: n for m, n in self._contacts.items()
                           if m.startswith("C") or m.startswith("R")}
                _save_contacts(friends, groups)
                self._rebuild_list()
                self.notify(f"已載入 {len(friends)} 位好友、{len(groups)} 個群組")
            else:
                msg = "聯絡人同步回傳 0 筆"
                self.notify(msg, severity="warning")
                with _LOG.open("a") as f:
                    f.write(f"[{datetime.now()}] {msg}\n")
            self.sub_title = "已連線"
        except Exception as e:
            self.sub_title = "已連線"
            self.notify(f"聯絡人同步失敗: {e}", severity="error")
            _log_exc("sync_contacts 失敗")

    async def _refresh_chat(self, mid: str) -> None:
        if not self._connected: return
        try:
            from fetch_messages import fetch_chat_messages
            token = await self._get_token()
            msgs  = await fetch_chat_messages(self._page, token, mid, 50)
            self._data[mid] = msgs
            _save_messages(self._data)
            self._show_messages(mid)
        except Exception as e:
            self.notify(f"重新整理失敗: {e}", severity="error")

    def action_unsend(self) -> None:
        if not self._connected or not self.current_chat:
            return
        lv   = self.query_one("#messages", ListView)
        item = lv.highlighted_child
        if not isinstance(item, MessageItem):
            self.notify("請先在對話區選擇訊息（按 m 進入）", severity="warning")
            return
        if not item.is_mine:
            self.notify("只能收回自己的訊息", severity="warning")
            return
        self.run_worker(self._do_unsend(item.msg_id), name="unsend")

    async def _do_unsend(self, msg_id: str) -> None:
        try:
            from send_api import unsend_message
            result = await unsend_message(self._page, msg_id)
            if result.get("ok"):
                mid = self.current_chat
                self._data[mid] = [m for m in self._data.get(mid, [])
                                   if m.get("id") != msg_id]
                _save_messages(self._data)
                self._show_messages(mid)
                self.notify("已收回訊息")
            else:
                self.notify(f"收回失敗: {result.get('error')}", severity="error")
        except Exception as e:
            self.notify(f"收回失敗: {e}", severity="error")
            _log_exc("unsend 失敗")

    async def _decrypt_chat(self, mid: str) -> None:
        """解密該聊天室所有未解密的 E2EE 訊息，解完後重繪。"""
        if not self._connected or not self._my_mid:
            return
        try:
            from send_api import decrypt_e2ee_message
            token   = await self._get_token()
            msgs    = self._data.get(mid, [])
            pending = [m for m in msgs
                       if (int(m.get("contentType", 0)) == 0
                           and m.get("text") is None
                           and m.get("chunks")
                           and m.get("from") != self._my_mid
                           and not m.get("_decrypt_skip"))]
            if not pending:
                return
            with _LOG.open("a") as f:
                f.write(f"[{datetime.now()}] decrypt_chat {mid[:12]} 開始，{len(pending)} 則待解密\n")
            ok = fail = 0
            for m in pending:
                text = await decrypt_e2ee_message(
                    self._page, m, self._my_mid, token,
                    self._ltsm_cache, self._chan_cache, self._pub_cache,
                    debug_log=_LOG if ok == 0 and fail <= 5 else None,  # 只診斷前幾則
                )
                if text is not None:
                    m["text"] = text
                    ok += 1
                else:
                    fail += 1
            with _LOG.open("a") as f:
                f.write(f"[{datetime.now()}] decrypt_chat 結束：成功 {ok}，失敗 {fail}\n")
            if ok:
                _save_messages(self._data)
                if self.current_chat == mid:
                    self._show_messages(mid)
        except Exception:
            _log_exc("decrypt_chat 失敗")

    # ── 渲染 ─────────────────────────────────────────────────────

    def _rebuild_list(self) -> None:
        chats = [(mid, max(int(m.get("createdTime", 0)) for m in msgs))
                 for mid, msgs in self._data.items() if msgs]
        chats.sort(key=lambda c: c[1], reverse=True)
        self._order         = [c[0] for c in chats]
        self._sidebar_chats = chats
        self._sidebar_shown = 0
        lv = self.query_one("#chat-list", ListView)
        lv.clear()
        self._append_sidebar_page(lv)

    def _append_sidebar_page(self, lv=None) -> None:
        if lv is None:
            lv = self.query_one("#chat-list", ListView)
        start = self._sidebar_shown
        end   = min(start + self._SIDEBAR_PAGE, len(self._sidebar_chats))
        for mid, _ in self._sidebar_chats[start:end]:
            msgs   = self._data[mid]
            last   = max(msgs, key=lambda m: int(m.get("createdTime", 0)))
            label  = self._contacts.get(mid, mid[:14] + "…")
            unread = len(self._unread.get(mid, set()))
            lv.append(ChatItem(mid, label, _preview(last), unread))
        self._sidebar_shown = end
        remaining = len(self._sidebar_chats) - end
        if remaining > 0:
            sentinel = ListItem(Label(f"[dim]↓ 還有 {remaining} 個[/]", markup=True))
            sentinel._is_sentinel = True
            lv.append(sentinel)

    def on_list_view_highlighted(self, ev: ListView.Highlighted) -> None:
        if not ev.item:
            return
        if getattr(ev.item, "_is_sentinel", False):
            ev.item.remove()
            self._append_sidebar_page()
        elif getattr(ev.item, "_is_hint", False):
            # 捲到頂端自動載入更早的訊息
            self.call_after_refresh(self.action_load_older)

    def _show_messages(self, mid: str) -> None:
        lv   = self.query_one("#messages", ListView)
        lv.clear()
        n    = self._chat_shown.get(mid, 80)
        msgs = sorted(self._data.get(mid, []),
                      key=lambda m: int(m.get("createdTime", 0)))
        total = len(msgs)
        if total > n:
            hint = ListItem(Label(f"[ 按 [ 載入更早的 {total - n} 則 ]", markup=False))
            hint._is_hint = True
            lv.append(hint)
        for m in msgs[-n:]:
            lv.append(MessageItem(m, self._my_mid, self._contacts))
        lv.scroll_end(animate=False)

    async def action_load_older(self) -> None:
        mid = self.current_chat
        if not mid: return
        msgs = sorted(self._data.get(mid, []), key=lambda m: int(m.get("createdTime", 0)))
        if not msgs: return
        if self._connected:
            from fetch_messages import _get_previous
            try:
                token = await self._get_token()
                prev  = await _get_previous(self._page, token, mid, msgs[0], 30)
                if prev:
                    known = {m["id"] for m in self._data[mid]}
                    new   = [m for m in prev if m["id"] not in known]
                    if new:
                        self._data[mid] = new + self._data[mid]
                        _save_messages(self._data)
            except Exception:
                _log_exc("load_older 失敗")
        self._chat_shown[mid] = self._chat_shown.get(mid, 80) + 30
        self._show_messages(mid)

    def _append_message(self, m: dict, chat_mid: str) -> None:
        lv = self.query_one("#messages", ListView)
        lv.append(MessageItem(m, self._my_mid, self._contacts))
        lv.scroll_end(animate=False)


if __name__ == "__main__":
    TuiApp().run()
