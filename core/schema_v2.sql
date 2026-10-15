-- PAPA core schema v2 (GENPLAN PAPA). Идемпотентно, только добавляет — v1 не ломает.
-- Материал из хаба: где лежит оригинал, есть ли медиа, для какого канала, срочный ли.
ALTER TABLE materials ADD COLUMN IF NOT EXISTS hub_chat_id      BIGINT;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS hub_message_id   BIGINT;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS has_media        BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE materials ADD COLUMN IF NOT EXISTS target_platform_id INT REFERENCES platforms(id);  -- NULL = любой канал
ALTER TABLE materials ADD COLUMN IF NOT EXISTS urgent           BOOLEAN NOT NULL DEFAULT false;
CREATE UNIQUE INDEX IF NOT EXISTS uq_materials_hub ON materials(hub_chat_id, hub_message_id) WHERE hub_chat_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_materials_pool ON materials(status, rubric, created_at);

-- Публикация в слоте сетки: какой слот (HH:MM) и какой рекламный заказ.
ALTER TABLE publications ADD COLUMN IF NOT EXISTS slot        TEXT CHECK (slot IS NULL OR slot ~ '^[0-2][0-9]:[0-5][0-9]$');
ALTER TABLE publications ADD COLUMN IF NOT EXISTS ad_order_id INT REFERENCES ad_orders(id);
ALTER TABLE publications ADD COLUMN IF NOT EXISTS error       TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_publications_slot
    ON publications(platform_id, slot, (published_at::date)) WHERE slot IS NOT NULL AND status = 'published';

-- Реклама на конкретный день и окно (фаза Reklama развернёт полностью).
ALTER TABLE ad_orders ADD COLUMN IF NOT EXISTS platform_id INT REFERENCES platforms(id);
ALTER TABLE ad_orders ADD COLUMN IF NOT EXISTS run_date    DATE;
ALTER TABLE ad_orders ADD COLUMN IF NOT EXISTS slot        TEXT;
ALTER TABLE ad_orders ADD COLUMN IF NOT EXISTS material_id BIGINT REFERENCES materials(id);

INSERT INTO schema_version(version) VALUES (2) ON CONFLICT DO NOTHING;
