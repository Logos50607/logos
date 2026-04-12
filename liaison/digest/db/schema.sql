-- schema.sql - liaison/digest PostgreSQL DDL
-- 語意層資料庫：賦予 channel 原始訊息意義，管理 identity、event 與 task

-- ── Identity ──────────────────────────────────────────────────────────

-- Property 型別定義（含基礎 seed，應用層負責驗證）
CREATE TABLE IF NOT EXISTS property_type (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT NOT NULL UNIQUE,
    value_type     TEXT NOT NULL DEFAULT 'text',  -- 'text' | 'enum' | 'date' | 'boolean'
    allow_multiple BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_values TEXT[],   -- enum 時列出合法選項，其他 NULL
    description    TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO property_type (name, value_type, allow_multiple, allowed_values, description) VALUES
    ('kind',             'enum',    false, ARRAY['personal','group'],                        'identity 類型：personal（自然人）或 group（組織／專案）'),
    ('real_name',        'text',    false, NULL,                                             '本名'),
    ('nickname',         'text',    true,  NULL,                                             '慣用暱稱，可多個'),
    ('birthday',         'date',    false, NULL,                                             '生日（YYYY-MM-DD）'),
    ('phone',            'text',    true,  NULL,                                             '電話號碼'),
    ('email',            'text',    true,  NULL,                                             'Email'),
    ('interest',         'text',    true,  NULL,                                             '興趣 / 關注領域'),
    ('sexual_orientation','enum',   true,  ARRAY['female','male','both','non-human'],        '性吸引對象，可多選'),
    ('fetish',           'text',    true,  NULL,                                             '性癖，自由填寫'),
    ('gender',           'enum',    false, ARRAY['male','female','non-binary','other'],      '性別'),
    ('occupation',       'text',    false, NULL,                                             '職稱 / 角色'),
    ('note',             'text',    true,  NULL,                                             '備註'),
    ('role',             'text',    false, NULL,                                             'relation 中的角色（如 PM、BD、技術主管）'),
    ('temporal',         'enum',    false, ARRAY['current','past'],                          '關係的時間性：current（現在）或 past（過去）')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS identity (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- identity 的屬性值（與 property_type 多對一）
CREATE TABLE IF NOT EXISTS identity_property (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id      UUID NOT NULL REFERENCES identity(id) ON DELETE CASCADE,
    property_type_id UUID NOT NULL REFERENCES property_type(id),
    value            TEXT NOT NULL,
    source           JSONB,   -- 推論來源：["msg_uuid1", "msg_uuid2"]，對應 line_official.messages.id
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ip_identity ON identity_property (identity_id);

-- identity 在各 channel 的帳號（跨 channel 對應）
CREATE TABLE IF NOT EXISTS identity_channel_participant (
    identity_id UUID NOT NULL REFERENCES identity(id) ON DELETE CASCADE,
    channel     TEXT NOT NULL,   -- 'line_personal' | 'line_official' | 'instagram' ...
    external_id TEXT NOT NULL,   -- platform 原始 participant ID
    PRIMARY KEY (channel, external_id)
);
CREATE INDEX IF NOT EXISTS icp_identity ON identity_channel_participant (identity_id);

-- 兩個 identity 之間的有向關係（人↔人、人↔組織、組織↔組織）
-- relation_type: 'colleague' | 'partner' | 'family' | 'friend' | 'client' | 'belongs_to' ...
CREATE TABLE IF NOT EXISTS identity_relation (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_identity_id UUID NOT NULL REFERENCES identity(id) ON DELETE CASCADE,
    to_identity_id   UUID NOT NULL REFERENCES identity(id) ON DELETE CASCADE,
    relation_type    TEXT NOT NULL,
    source           JSONB,   -- 推論來源：["msg_uuid1", "msg_uuid2"]，對應 line_official.messages.id
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ir_from ON identity_relation (from_identity_id);
CREATE INDEX IF NOT EXISTS ir_to   ON identity_relation (to_identity_id);

-- relation 的屬性值（如 role: PM、BD；note: 說明文字）
CREATE TABLE IF NOT EXISTS identity_relation_property (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relation_id      UUID NOT NULL REFERENCES identity_relation(id) ON DELETE CASCADE,
    property_type_id UUID NOT NULL REFERENCES property_type(id),
    value            TEXT NOT NULL,
    source           JSONB,   -- 推論來源：["msg_uuid1", "msg_uuid2"]，對應 line_official.messages.id
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS irp_relation ON identity_relation_property (relation_id);

-- ── Event ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS event (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary                TEXT,
    category               TEXT NOT NULL,   -- 'task' | 'question' | 'info' | 'social' | 'alert' | 'unknown'
    priority               TEXT NOT NULL,   -- 'critical' | 'high' | 'normal' | 'low'
    occurred_at            TIMESTAMPTZ NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reported_at            TIMESTAMPTZ,
    source_conversation_id TEXT             -- channel 端的 conversation external_id（群組或個人對話）
);
CREATE INDEX IF NOT EXISTS event_occurred ON event (occurred_at DESC);
CREATE INDEX IF NOT EXISTS event_priority ON event (priority, occurred_at DESC);

-- event 與 channel 原始訊息的多對多
CREATE TABLE IF NOT EXISTS event_message (
    event_id            UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    external_message_id TEXT NOT NULL,
    PRIMARY KEY (event_id, external_message_id)
);

-- event 涉及哪些 identity
CREATE TABLE IF NOT EXISTS event_identity (
    event_id    UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    identity_id UUID NOT NULL REFERENCES identity(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,   -- 'sender' | 'mentioned' | 'recipient'
    PRIMARY KEY (event_id, identity_id, role)
);
CREATE INDEX IF NOT EXISTS ei_identity ON event_identity (identity_id);

-- ── Task ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS task (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    description     TEXT,
    source_event_id UUID REFERENCES event(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS task_source ON task (source_event_id);

-- task 狀態變更日誌（當前狀態 = 最後一筆 status）
CREATE TABLE IF NOT EXISTS task_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id    UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    event_id   UUID REFERENCES event(id) ON DELETE SET NULL,   -- 觸發此次變更的 event
    status     TEXT NOT NULL,   -- 'open' | 'in_progress' | 'done' | 'cancelled'
    notes      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS tl_task ON task_log (task_id, created_at DESC);

-- ── Views ─────────────────────────────────────────────────────────────

-- task 當前狀態（取最後一筆 task_log）
CREATE OR REPLACE VIEW task_current_status AS
SELECT DISTINCT ON (t.id)
    t.id,
    t.title,
    t.description,
    t.source_event_id,
    tl.status,
    tl.created_at AS status_changed_at,
    t.created_at
FROM task t
JOIN task_log tl ON tl.task_id = t.id
ORDER BY t.id, tl.created_at DESC;

-- 未呈報的 event（供掃描器查詢待處理清單）
CREATE OR REPLACE VIEW pending_events AS
SELECT * FROM event
WHERE reported_at IS NULL
ORDER BY priority DESC, occurred_at DESC;
