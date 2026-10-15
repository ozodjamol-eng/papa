# Ядро PAPA: отдельная база `papa` в уже работающем PostgreSQL. Настройки PostgreSQL и другие базы не трогаются, перезапуска нет.
set -Eeuo pipefail
command -v psql >/dev/null || { echo NO_POSTGRES_CLIENT; exit 1; }
systemctl is-active --quiet postgresql || { echo POSTGRES_NOT_ACTIVE; exit 1; }
PSQL="runuser -u postgres -- psql -X -v ON_ERROR_STOP=1 -q"
echo "postgres: $($PSQL -d postgres -Atc 'show server_version')"
$PSQL -d postgres -Atc "select 1 from pg_roles where rolname='papa'" | grep -q 1 || $PSQL -d postgres -c "CREATE ROLE papa NOLOGIN"
$PSQL -d postgres -Atc "select 1 from pg_database where datname='papa'" | grep -q 1 || $PSQL -d postgres -c "CREATE DATABASE papa OWNER papa ENCODING 'UTF8' TEMPLATE template0"
install -m 644 /opt/papa/core/schema.sql /tmp/papa-schema.sql
$PSQL -d papa -c "SET client_min_messages=warning" -f /tmp/papa-schema.sql
rm -f /tmp/papa-schema.sql
echo "таблиц: $($PSQL -d papa -Atc "select count(*) from information_schema.tables where table_schema='public'")  пространств: $($PSQL -d papa -Atc 'select count(*) from spaces')  площадок: $($PSQL -d papa -Atc 'select count(*) from platforms')  версия схемы: $($PSQL -d papa -Atc 'select max(version) from schema_version')"
echo "размер базы: $($PSQL -d postgres -Atc "select pg_size_pretty(pg_database_size('papa'))")"
echo "genplan=$(systemctl is-active xojaobod-genplan-v3) city24=$(systemctl is-active xojaobodcity24bot) goldwater=$(systemctl is-active goldwater-bot)"
echo "== CORE_INSTALLED"
