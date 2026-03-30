# /// script
# dependencies = ["textual", "playwright", "cryptography"]
# ///
"""
tui.py - LINE 個人帳號 Terminal UI

用法: uv run tui.py
操作:
  ↑↓       切換聊天室          n    新對話（聯絡人/群組）
  Enter    開啟聊天            r    重新整理
  Tab      聊天清單 ↔ 輸入框   q    離開
  Escape   回聊天清單 / 關閉
"""

# 目錄:
# 1. 常數 & 輔助函式
# 2. ChatItem widget
# 3. ContactPickerScreen modal
# 4. TuiApp：compose / on_mount / 事件處理
# 5. TuiApp：非同步任務 (cdp / preload / send / poll / contacts / refresh)
# 6. TuiApp：渲染 (rebuild_list / show_messages / append_message)

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
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog

ROOT   = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

_MSGS  = ROOT / "messages.json"
_NAMES = Path(__file__).parent / "contacts.json"

_CT = {
    0:  "",
    1:  "📷 圖片",
    2:  "🎬 影片",
    3:  "🎵 音訊",
    7:  "🔖 貼圖",
    13: "📇 聯絡人名片",
    14: "📎 檔案",
    15: "📍 位置",
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
    if ct == 0:  return str(m.get("text", ""))[:40]
    if ct == 14: return f"📎 {_meta(m).get('FILE_NAME', '檔案')}"
    dur = _meta(m).get("DURATION")
    if dur:      return f"{_CT.get(ct,'?')} ({int(dur)//1000}s)"
    return _CT.get(ct, f"[type {ct}]")

def _load_contacts() -> dict:
    return json.loads(_NAMES.read_text()) if _NAMES.exists() else {}

def _load_messages() -> dict:
    return json.loads(_MSGS.read_text()) if _MSGS.exists() else {}

def _save_messages(data: dict) -> None:
    _MSGS.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ── 2. ChatItem ───────────────────────────────────────────────────

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
#messages { height: 1fr; padding: 0 1; }
#input-row { height: 3; dock: bottom; }
#input { width: 1fr; }
ChatItem { height: 4; padding: 0 1; }
ChatItem.--highlight { background: $primary-darken-1; }
"""

class TuiApp(App):
    CSS = CSS
    BINDINGS = [
        Binding("q",      "quit",       "離開"),
        Binding("n",      "new_chat",   "新對話"),
        Binding("r",      "refresh",    "重新整理"),
        Binding("escape", "focus_list", "聊天清單"),
        Binding("tab",    "focus_input","輸入框", show=False),
    ]
    current_chat: reactive[str | None] = reactive(None)

    def __init__(self):
        super().__init__()
        self._data:     dict           = {}
        self._contacts: dict           = {}
        self._my_mid:   str | None     = None
        self._page                     = None
        self._connected: bool          = False
        self._order:    list[str]      = []
        self._unread:   dict[str, set] = {}
        self._token:    str | None     = None
        self._token_ts: float          = 0.0
        self._pw                       = None
        self._browser                  = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label("[b] 聊天室[/]", markup=True)
                yield ListView(id="chat-list")
            with Vertical(id="main"):
                yield RichLog(id="messages", highlight=True, markup=True, wrap=True)
                with Horizontal(id="input-row"):
                    yield Input(placeholder="輸入訊息… [Enter 送出]", id="input")
        yield Footer()

    def on_mount(self) -> None:
        self.title     = "LINE Personal"
        self.sub_title = "連線中…"
        self._data     = _load_messages()
        self._contacts = _load_contacts()
        self._rebuild_list()
        self.run_worker(self._connect_cdp(), exclusive=True, name="cdp")
        self.set_interval(30, self._poll)

    # ── 事件處理 ─────────────────────────────────────────────────

    def on_list_view_selected(self, ev: ListView.Selected) -> None:
        item = ev.item
        if isinstance(item, ChatItem):
            self.current_chat = item.mid
            self._unread.pop(item.mid, None)
            self._show_messages(item.mid)
            self.query_one("#input", Input).focus()

    async def on_input_submitted(self, ev: Input.Submitted) -> None:
        text = ev.value.strip()
        if not text or not self.current_chat:
            return
        ev.input.clear()
        if not self._connected:
            self.notify("尚未連線，請稍候", severity="warning"); return
        self.run_worker(self._send(self.current_chat, text), name="send")

    def action_focus_list(self)  -> None: self.query_one("#chat-list").focus()
    def action_focus_input(self) -> None: self.query_one("#input").focus()

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

    async def on_unmount(self) -> None:
        """退出時關閉 Playwright，避免 terminal 凍結。"""
        if self._browser:
            try: await self._browser.close()
            except Exception: pass
        if self._pw:
            try: await self._pw.stop()
            except Exception: pass

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
            self.run_worker(self._sync_contacts(), name="contacts")
            self.run_worker(self._preload_recent(), name="preload")
        except Exception as e:
            self.notify(f"連線失敗: {e}", severity="error")

    async def _preload_recent(self) -> None:
        """分批載入所有聊天室訊息，標題顯示進度，每 5 筆存一次。"""
        try:
            from fetch_messages import fetch_chat_messages
            token = await self._get_token()
            order = list(self._order)   # snapshot，避免 rebuild 期間變動
            total = len(order)
            for i, mid in enumerate(order):
                self.sub_title = f"載入 {i+1}/{total}…"
                msgs = await fetch_chat_messages(self._page, token, mid, 30)
                if msgs:
                    self._data[mid] = msgs
                self._rebuild_list()
                if self.current_chat == mid:
                    self._show_messages(mid)
                if i % 5 == 4:
                    _save_messages(self._data)
            _save_messages(self._data)
            self.sub_title = "已連線"
            self.notify(f"全部 {total} 個聊天室載入完成 ✓")
        except Exception as e:
            self.sub_title = "已連線"
            self.log.error(f"preload: {e}")

    async def _send(self, mid: str, text: str) -> None:
        from send_api import send_e2ee_text
        result = await send_e2ee_text(self._page, mid, text)
        if result.get("ok"):
            msg = {"from": self._my_mid or "", "to": mid,
                   "contentType": 0, "text": text,
                   "createdTime": str(int(time.time() * 1000)),
                   "id": f"local-{result['seq']}"}
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
        try:
            from gw_client import get_access_token
            from fetch_messages import fetch_chat_messages
            token   = await get_access_token(self._page)
            changed = False
            for mid in self._order:
                known = {m["id"] for m in self._data.get(mid, [])}
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
            if changed:
                _save_messages(self._data)
        except Exception as e:
            self.log.error(f"poll: {e}")

    async def _sync_contacts(self) -> None:
        try:
            from fetch_contacts import fetch_contacts
            new = await fetch_contacts(self._page, await self._get_token())
            if new:
                self._contacts.update(new)
                _NAMES.write_text(json.dumps(self._contacts, ensure_ascii=False, indent=2))
                self._rebuild_list()
                self.notify(f"已載入 {len(new)} 個聯絡人名稱")
        except Exception as e:
            self.log.error(f"sync_contacts: {e}")

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

    # ── 渲染 ─────────────────────────────────────────────────────

    def _rebuild_list(self) -> None:
        chats = [(mid, max(int(m.get("createdTime", 0)) for m in msgs))
                 for mid, msgs in self._data.items() if msgs]
        chats.sort(key=lambda c: c[1], reverse=True)
        self._order = [c[0] for c in chats]
        lv = self.query_one("#chat-list", ListView)
        lv.clear()
        for mid, _ in chats:
            msgs   = self._data[mid]
            last   = max(msgs, key=lambda m: int(m.get("createdTime", 0)))
            label  = self._contacts.get(mid, mid[:14] + "…")
            unread = len(self._unread.get(mid, set()))
            lv.append(ChatItem(mid, label, _preview(last), unread))

    def _show_messages(self, mid: str) -> None:
        log  = self.query_one("#messages", RichLog)
        log.clear()
        name = self._contacts.get(mid, mid[:14] + "…")
        log.write(f"[bold cyan]── {name} ──[/]\n")
        msgs = sorted(self._data.get(mid, []),
                      key=lambda m: int(m.get("createdTime", 0)))
        for m in msgs[-80:]:
            self._append_message(m, mid)

    def _append_message(self, m: dict, chat_mid: str) -> None:
        log     = self.query_one("#messages", RichLog)
        ct      = int(m.get("contentType", 0))
        text    = _preview(m) if ct != 0 else str(m.get("text", ""))
        ts      = _ts(m.get("createdTime", 0))
        is_mine = bool(self._my_mid and m.get("from") == self._my_mid)
        if is_mine:
            log.write(Align.right(Text.assemble(
                (text, "bold green"), "  ", (ts, "dim"))))
        else:
            sender = self._contacts.get(m.get("from", ""), "")
            prefix = Text(f"{sender} ", style="cyan bold") if sender else Text("")
            log.write(Text.assemble(prefix, (text, "white"), "  ", (ts, "dim")))


if __name__ == "__main__":
    TuiApp().run()
