-- PAPA core schema v1 (PostgreSQL). Идемпотентно: можно применять повторно.
-- Общая память модулей: пространства, площадки, источники, аудитория, материалы, публикации, реклама, события.

CREATE TABLE IF NOT EXISTS schema_version (version INT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());

-- Пространство: проект/бренд (Xo'jaobod City, Paparazzi, GOLD WATER, позже клиенты)
CREATE TABLE IF NOT EXISTS spaces (
    id          SERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{2,40}$'),
    title       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Площадка: конкретный канал/аккаунт внутри пространства
CREATE TABLE IF NOT EXISTS platforms (
    id           SERIAL PRIMARY KEY,
    space_id     INT NOT NULL REFERENCES spaces(id),
    kind         TEXT NOT NULL CHECK (kind IN ('telegram_channel','telegram_group','telegram_bot','instagram','youtube','site')),
    handle       TEXT,                       -- @username / адрес
    external_id  TEXT,                       -- id на площадке
    title        TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'audience' CHECK (role IN ('audience','monetization','test')),
    active       BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kind, external_id)
);

-- Источник: ссылка с меткой (какой рилс/видео/сторис привёл человека)
CREATE TABLE IF NOT EXISTS sources (
    id                 SERIAL PRIMARY KEY,
    code               TEXT NOT NULL UNIQUE CHECK (code ~ '^[a-z0-9_-]{3,64}$'),
    target_platform_id INT NOT NULL REFERENCES platforms(id),   -- куда ведёт (канал)
    origin_platform_id INT REFERENCES platforms(id),            -- где размещена (Instagram, YouTube)
    title              TEXT NOT NULL,
    invite_link        TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Аудитория: человек — только идентификатор и путь, без телефонов и переписок
CREATE TABLE IF NOT EXISTS contacts (
    id               BIGSERIAL PRIMARY KEY,
    kind             TEXT NOT NULL CHECK (kind IN ('telegram','instagram','youtube')),
    external_id      TEXT NOT NULL,
    first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    first_source_id  INT REFERENCES sources(id),
    UNIQUE (kind, external_id)
);

CREATE TABLE IF NOT EXISTS memberships (
    contact_id   BIGINT NOT NULL REFERENCES contacts(id),
    platform_id  INT NOT NULL REFERENCES platforms(id),
    status       TEXT NOT NULL CHECK (status IN ('requested','joined','left')),
    source_id    INT REFERENCES sources(id),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (contact_id, platform_id)
);

-- Материал: единица контента и её жизненный цикл
CREATE TABLE IF NOT EXISTS materials (
    id          BIGSERIAL PRIMARY KEY,
    space_id    INT NOT NULL REFERENCES spaces(id),
    origin      TEXT NOT NULL CHECK (origin IN ('razvedka','fabrika','manual','genplan')),
    status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','scheduled','published','rejected')),
    rubric      TEXT,
    text        TEXT,
    media       JSONB NOT NULL DEFAULT '[]',
    origin_ref  TEXT,                        -- откуда взят (канал:сообщение), для проверки уникальности
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(space_id, status);

-- Публикация: материал на площадке, когда вышел, сколько набрал
CREATE TABLE IF NOT EXISTS publications (
    id            BIGSERIAL PRIMARY KEY,
    material_id   BIGINT REFERENCES materials(id),
    platform_id   INT NOT NULL REFERENCES platforms(id),
    planned_at    TIMESTAMPTZ,
    published_at  TIMESTAMPTZ,
    message_id    TEXT,
    status        TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','published','failed','cancelled')),
    is_ad         BOOLEAN NOT NULL DEFAULT false,
    views         JSONB NOT NULL DEFAULT '{}',   -- {"1h":..,"24h":..,"7d":..}
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_publications_platform_time ON publications(platform_id, published_at);

-- Реклама (наполняется в фазе Reklama)
CREATE TABLE IF NOT EXISTS ad_orders (
    id           SERIAL PRIMARY KEY,
    space_id     INT NOT NULL REFERENCES spaces(id),
    advertiser   TEXT NOT NULL,
    price        NUMERIC(14,2),
    currency     TEXT NOT NULL DEFAULT 'UZS',
    status       TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','agreed','paid','done','cancelled')),
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ad_placements (
    order_id        INT NOT NULL REFERENCES ad_orders(id),
    publication_id  BIGINT NOT NULL REFERENCES publications(id),
    PRIMARY KEY (order_id, publication_id)
);

-- Журнал событий: только добавление, изменить или удалить нельзя
CREATE TABLE IF NOT EXISTS events (
    id              BIGSERIAL PRIMARY KEY,
    at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind            TEXT NOT NULL,
    module          TEXT NOT NULL,
    space_id        INT REFERENCES spaces(id),
    platform_id     INT REFERENCES platforms(id),
    contact_id      BIGINT REFERENCES contacts(id),
    source_id       INT REFERENCES sources(id),
    publication_id  BIGINT REFERENCES publications(id),
    data            JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_kind_at ON events(kind, at);

CREATE OR REPLACE FUNCTION papa_events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'events is append-only'; END $$;
DROP TRIGGER IF EXISTS events_no_change ON events;
CREATE TRIGGER events_no_change BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION papa_events_append_only();

-- Стартовые пространства и площадки (без секретов)
INSERT INTO spaces(slug, title) VALUES
    ('xojaobod-city', 'Xo''jaobod City'), ('paparazzi', 'PaparazziUZ'), ('goldwater', 'GOLD WATER')
ON CONFLICT (slug) DO NOTHING;
INSERT INTO platforms(space_id, kind, handle, external_id, title, role)
SELECT s.id, v.kind, v.handle, v.ext, v.title, v.role FROM (VALUES
    ('xojaobod-city', 'telegram_group',   'xojaobodcity24', 'tg:xojaobodcity24', 'XO''JAOBOD CITY 24', 'monetization'),
    ('paparazzi',     'telegram_channel', 'ozodjamoll',     'tg:ozodjamoll',     'PaparazziUZ',        'monetization')
) AS v(space, kind, handle, ext, title, role) JOIN spaces s ON s.slug = v.space
ON CONFLICT (kind, external_id) DO NOTHING;

INSERT INTO schema_version(version) VALUES (1) ON CONFLICT DO NOTHING;
