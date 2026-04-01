# /// script
# dependencies = ["textual", "cryptography"]
# ///
"""
tui.py - LINE 個人帳號 Terminal UI（純 file-based，資料由 sync.py daemon 提供）

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
# 6. TuiApp：非同步任務 (send / poll / check_files)
# 7. TuiApp：渲染 (rebuild_list / show_messages / append_message)

import ast, json, sys, time
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.table import Table
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
_PUBKEYS = _DATA / "pubkeys.json"
_OUTBOX     = _DATA / "outbox.json"
_STATE      = _DATA / "state.json"
_TUI_ACTIVE = _DATA / "tui_active"
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

# Rich 顏色名 → Textual CSS 相容顏色（styles.background 使用）
_RICH_TO_CSS: dict[str, str] = {
    "bright_cyan":    "ansi_bright_cyan",
    "bright_yellow":  "ansi_bright_yellow",
    "bright_magenta": "ansi_bright_magenta",
    "bright_green":   "ansi_bright_green",
    "bright_blue":    "ansi_bright_blue",
    "orange1":        "#ff8700",
    "chartreuse3":    "#5faf00",
    "deep_sky_blue1": "#00afff",
    "hot_pink":       "#ff69b4",
}

def _css_color(rich_name: str) -> str:
    return _RICH_TO_CSS.get(rich_name, rich_name)

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
    try:
        dt = datetime.fromtimestamp(int(ms) / 1000).astimezone()
        return dt.strftime("%H:%M ") + dt.strftime("%Z")
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


def _name_ts_row(name: str, ts: str) -> Text:
    """名字 + 兩格空白 + 灰色時間。"""
    return Text.assemble((name, "bold white"), ("  ", ""), (ts, "dim"))


# ── 2. MessageItem ────────────────────────────────────────────────

class MessageItem(ListItem):
    """對話氣泡：可選取（Enter 回覆，d 收回自己的）。"""

    def __init__(self, msg: dict, my_mid: str | None, contacts: dict):
        super().__init__()
        self._msg      = msg
        self._my_mid   = my_mid
        self._contacts = contacts
        if my_mid and msg.get("from") == my_mid:
            self.add_class("--mine")

    @property
    def msg_id(self) -> str:
        return self._msg.get("id", "")

    @property
    def is_mine(self) -> bool:
        return bool(self._my_mid and self._msg.get("from") == self._my_mid)

    def _build_text(self) -> str:
        if self._msg.get("_unsent"):
            return "[已收回]"
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
            name   = self._contacts.get(sender_mid, "我")
            yield Static(Align.right(_name_ts_row(name, ts)), classes="name-row")
            yield Static(Text(text), classes="bubble")
        else:
            color  = _sender_style(sender_mid)
            sender = self._contacts.get(sender_mid, sender_mid[:10])
            css_bg = _css_color(color)
            if sender:
                yield Static(_name_ts_row(sender, ts), classes="name-row")
            text_s = Static(Text(text), classes="bubble")
            text_s.styles.background = css_bg
            text_s.styles.color = "black"
            yield text_s


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
MessageItem { height: auto; }
.name-row { width: 1fr; }
MessageItem.--mine { align-horizontal: right; }
MessageItem.--mine > .bubble { background: #00af00; color: black; }
.bubble { padding: 0 1; width: 85%; }
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
        self._msgs_mtime:    float          = 0.0
        self._order:         list[str]      = []
        self._unread:        dict[str, set] = {}
        self._sidebar_chats: list           = []   # 完整排序後的 (mid, ts) 清單
        self._sidebar_shown: int            = 0    # 已顯示幾筆
        self._chat_shown:    dict[str, int] = {}   # 各聊天室目前顯示幾則
        self._reply_to:      dict | None    = None  # 目前選取要回覆的訊息
        self._contacts_mtime: float        = 0.0

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
        self.title = "LINE Personal"
        _TUI_ACTIVE.touch()
        with _LOG.open("a") as f:
            f.write(f"\n[{datetime.now()}] ── TUI 啟動 ──\n")
        _migrate_legacy()
        self._data     = _load_messages()
        self._contacts = _load_contacts()
        self._msgs_mtime = _MSGS.stat().st_mtime if _MSGS.exists() else 0.0
        self._contacts_mtime = max(
            (_FRIENDS.stat().st_mtime if _FRIENDS.exists() else 0.0),
            (_GROUPS.stat().st_mtime  if _GROUPS.exists()  else 0.0),
        )
        if _STATE.exists():
            self._my_mid = json.loads(_STATE.read_text()).get("my_mid")
        self._update_status()
        self._rebuild_list()
        self.set_interval(5, self._check_files)

    # ── 事件處理 ─────────────────────────────────────────────────

    def on_list_view_selected(self, ev: ListView.Selected) -> None:
        item = ev.item
        if isinstance(item, ChatItem):
            self.current_chat = item.mid
            self._unread.pop(item.mid, None)
            self._show_messages(item.mid)
            self.query_one("#input", Input).focus()
        elif isinstance(item, MessageItem):
            self._reply_to = item._msg
            preview = str(item._msg.get("text", _preview(item._msg)))[:50]
            bar = self.query_one("#reply-bar", Label)
            bar.update(f"↩ 回覆: {preview}")
            bar.display = True
            self.query_one("#input", Input).focus()

    def on_input_submitted(self, ev: Input.Submitted) -> None:
        text = ev.value.strip()
        if not text or not self.current_chat:
            return
        ev.input.clear()
        self._send(self.current_chat, text)

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
        self._data     = _load_messages()
        self._contacts = _load_contacts()
        self._msgs_mtime = _MSGS.stat().st_mtime if _MSGS.exists() else 0.0
        self._update_status()
        self._rebuild_list()
        if self.current_chat:
            self._show_messages(self.current_chat)

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

    def action_quit(self) -> None:
        """直接強制退出，kill 整個 process group（Python + uv 同時死，shell 立刻拿回 terminal）。"""
        import os, signal, termios
        _TUI_ACTIVE.unlink(missing_ok=True)
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

    # ── 任務（純 file-based，無 CDP）────────────────────────────

    def _update_status(self) -> None:
        """從 state.json 讀取 daemon 狀態，更新 sub_title。"""
        if not _STATE.exists():
            self.sub_title = "等待 sync.py 啟動…"
            return
        try:
            state = json.loads(_STATE.read_text())
            age   = int(time.time()) - int(state.get("ts", 0))
            if age < 30:
                self.sub_title = f"daemon 正常（{age}s 前）"
            else:
                self.sub_title = f"daemon 無回應（{age}s 前）"
        except Exception:
            self.sub_title = "state.json 讀取失敗"

    async def _check_files(self) -> None:
        """每 5 秒檢查檔案是否有更新，有則重新載入。"""
        try:
            # 檢查聯絡人
            new_ct = max(
                (_FRIENDS.stat().st_mtime if _FRIENDS.exists() else 0.0),
                (_GROUPS.stat().st_mtime  if _GROUPS.exists()  else 0.0),
            )
            if new_ct > self._contacts_mtime:
                self._contacts_mtime = new_ct
                self._contacts = _load_contacts()
                self._rebuild_list()

            # 檢查訊息
            new_mt = _MSGS.stat().st_mtime if _MSGS.exists() else 0.0
            if new_mt <= self._msgs_mtime:
                self._update_status()
                return
            self._msgs_mtime = new_mt
            old_ids = {mid: {m["id"] for m in msgs}
                       for mid, msgs in self._data.items()}
            self._data = _load_messages()

            # 找出新訊息，發通知 & 更新 unread
            for mid, msgs in self._data.items():
                known = old_ids.get(mid, set())
                new   = [m for m in msgs if m["id"] not in known]
                if not new:
                    continue
                self._unread.setdefault(mid, set()).update(m["id"] for m in new)
                if mid != self.current_chat:
                    print("\a", end="", flush=True)
                    label = self._contacts.get(mid, mid[:12] + "…")
                    self.notify(f"💬 {label}: {_preview(new[-1])}")

            self._rebuild_list()
            if self.current_chat:
                self._show_messages(self.current_chat)
            self._update_status()
        except Exception:
            _log_exc("check_files 失敗")

    def _send(self, mid: str, text: str) -> None:
        """寫入 outbox.json（由 sync.py daemon 發送），樂觀顯示。"""
        import uuid
        local_id = f"local-{uuid.uuid4().hex[:8]}"
        reply_id = self._reply_to["id"] if self._reply_to else None

        # 寫入 outbox
        try:
            outbox = json.loads(_OUTBOX.read_text()) if _OUTBOX.exists() else []
            entry: dict = {"local_id": local_id, "to": mid, "text": text}
            if reply_id:
                entry["reply_to_id"] = reply_id
            outbox.append(entry)
            tmp = _OUTBOX.with_suffix(".tmp")
            tmp.write_text(json.dumps(outbox, ensure_ascii=False))
            tmp.rename(_OUTBOX)
        except Exception as e:
            self.notify(f"outbox 寫入失敗: {e}", severity="error")
            _log_exc("send outbox 寫入失敗")
            return

        # 樂觀顯示（不寫 messages.json，等 daemon 回寫）
        msg: dict = {
            "from": self._my_mid or "", "to": mid,
            "contentType": 0, "text": text,
            "createdTime": str(int(time.time() * 1000)),
            "id": local_id,
        }
        if reply_id:
            msg["relatedMessageId"]    = reply_id
            msg["messageRelationType"] = 3

        # 清除回覆狀態
        self._reply_to = None
        bar = self.query_one("#reply-bar", Label)
        bar.update("")
        bar.display = False

        self._data.setdefault(mid, []).append(msg)
        if self.current_chat == mid:
            self._append_message(msg, mid)

    def action_unsend(self) -> None:
        if not self.current_chat:
            return
        lv   = self.query_one("#messages", ListView)
        item = lv.highlighted_child
        if not isinstance(item, MessageItem):
            self.notify("請先在對話區選擇訊息（按 m 進入）", severity="warning")
            return
        if not item.is_mine:
            self.notify("只能收回自己的訊息", severity="warning")
            return
        msg_id = item.msg_id
        try:
            outbox = json.loads(_OUTBOX.read_text()) if _OUTBOX.exists() else []
            outbox.append({"action": "unsend", "msg_id": msg_id,
                           "mid": self.current_chat})
            tmp = _OUTBOX.with_suffix(".tmp")
            tmp.write_text(json.dumps(outbox, ensure_ascii=False))
            tmp.rename(_OUTBOX)
            self.notify("已排入收回，等待 daemon 執行")
        except Exception as e:
            self.notify(f"收回失敗: {e}", severity="error")
            _log_exc("unsend outbox 寫入失敗")

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

    def action_load_older(self) -> None:
        mid = self.current_chat
        if not mid: return
        self._chat_shown[mid] = self._chat_shown.get(mid, 80) + 30
        self._show_messages(mid)

    def _append_message(self, m: dict, chat_mid: str) -> None:
        lv = self.query_one("#messages", ListView)
        lv.append(MessageItem(m, self._my_mid, self._contacts))
        lv.scroll_end(animate=False)


if __name__ == "__main__":
    TuiApp().run()
