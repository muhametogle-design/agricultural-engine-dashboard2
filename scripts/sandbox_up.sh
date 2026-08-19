#!/usr/bin/env bash
# Idempotent sandbox bring-up: system packages, python deps, DB cluster init.
# Server processes themselves are started separately (postgres, uvicorn).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v /usr/lib/postgresql/17/bin/pg_ctl >/dev/null 2>&1; then
  echo "[up] installing postgresql/postgis via apt"
  sudo -n apt-get update -qq
  sudo -n DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgis postgresql-contrib
fi

if ! python -c "import fastapi" >/dev/null 2>&1; then
  echo "[up] installing python requirements"
  pip install --quiet -r requirements.txt rasterio
  pip install --quiet pytest pytest-asyncio respx
fi

if [ ! -f /home/user/.db/pgdata/PG_VERSION ]; then
  echo "[up] initializing postgres cluster"
  mkdir -p /home/user/.db
  /usr/lib/postgresql/17/bin/initdb -D /home/user/.db/pgdata -U postgres --auth=trust --encoding=UTF8 >/dev/null
fi

# snapshot restores loosen cluster permissions AND drop empty subdirectories;
# postgres refuses to start until both are repaired
chmod 0700 /home/user/.db/pgdata 2>/dev/null || true
mkdir -p /home/user/.db/pgdata/{pg_commit_ts,pg_dynshmem,pg_notify,pg_replslot,pg_serial,pg_snapshots,pg_stat,pg_stat_tmp,pg_tblspc,pg_twophase,pg_logical/mappings,pg_logical/snapshots,pg_multixact/members,pg_multixact/offsets} 2>/dev/null || true
echo "[up] base packages ready (start postgres + api processes next)"
