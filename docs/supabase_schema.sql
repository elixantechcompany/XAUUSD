-- ============================================================
-- Supabase Schema — XAUUSD/BTCUSD Trading Bot Dashboard
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor)
-- All timestamps are UTC.
-- ============================================================

-- ── Heartbeats ────────────────────────────────────────────────────────────────
create table if not exists heartbeats (
  id            bigserial primary key,
  ts            timestamptz not null default now(),
  mt5_connected boolean     not null default false,
  last_tick_ts  timestamptz,
  equity        numeric(18,2),
  balance       numeric(18,2),
  execution_mode text        not null default 'paper',
  live_trading_enabled boolean not null default false
);

-- Keep only last 24h of heartbeats (RLS will handle read access)
create index if not exists idx_heartbeats_ts on heartbeats(ts desc);

-- ── Account snapshots ─────────────────────────────────────────────────────────
create table if not exists accounts_snapshot (
  id                    bigserial primary key,
  ts                    timestamptz not null default now(),
  equity                numeric(18,2),
  balance               numeric(18,2),
  daily_pnl             numeric(18,2),
  drawdown_pct          numeric(8,4),
  open_positions_count  int default 0,
  execution_mode        text not null default 'paper'
);

create index if not exists idx_accounts_snapshot_ts on accounts_snapshot(ts desc);

-- ── Signals ───────────────────────────────────────────────────────────────────
create table if not exists signals (
  id                  text primary key,           -- setup_id (SHA-256 prefix)
  created_at          timestamptz not null,
  updated_at          timestamptz not null,
  instrument          text not null,              -- XAUUSD | BTCUSD
  timeframe           text not null default 'H1',
  direction           text not null,              -- BULLISH | BEARISH
  state               text not null,              -- engine SetupState
  status              text not null default 'new',-- new|taken|skipped|expired|cancelled|hit_tp_or_sl
  fvg_low             numeric(18,5),
  fvg_high            numeric(18,5),
  sweep_level         numeric(18,5),
  sweep_extreme       numeric(18,5),
  ref_candle_high     numeric(18,5),
  ref_candle_low      numeric(18,5),
  trigger_level       numeric(18,5),
  entry               numeric(18,5),
  stop_loss           numeric(18,5),
  take_profit         numeric(18,5),
  suggested_lot_size  numeric(10,4),
  estimated_risk_usd  numeric(18,2),
  rr_ratio            numeric(8,4),
  rejection_reason    text,
  session             text,                       -- Asia|London|NewYork|Overlap
  quality_grade       text,                       -- A|B|C
  strategy_version    text not null default '1.0',
  outcome             text,                       -- win|loss|breakeven
  closed_at           timestamptz,
  r_multiple          numeric(8,4)
);

create index if not exists idx_signals_instrument on signals(instrument);
create index if not exists idx_signals_status on signals(status);
create index if not exists idx_signals_created on signals(created_at desc);

-- ── Evaluations ───────────────────────────────────────────────────────────────
create table if not exists evaluations (
  id              bigserial primary key,
  ts              timestamptz not null default now(),
  instrument      text not null,
  timeframe       text not null,
  decision        text not null,   -- SIGNAL|NO_TRADE|REJECTED|EXPIRED
  reason_codes    text[],
  indicators_json jsonb,
  session         text
);

create index if not exists idx_evaluations_ts on evaluations(ts desc);
create index if not exists idx_evaluations_instrument on evaluations(instrument, ts desc);

-- ── Trades ────────────────────────────────────────────────────────────────────
create table if not exists trades (
  ticket          text primary key,
  signal_id       text references signals(id),
  source          text not null default 'bot',  -- bot|manual|paper
  instrument      text not null,
  side            text not null,                -- BULLISH|BEARISH
  lots            numeric(10,4) not null,
  open_time       timestamptz not null,
  open_price      numeric(18,5) not null,
  sl              numeric(18,5),
  tp              numeric(18,5),
  close_time      timestamptz,
  close_price     numeric(18,5),
  pnl             numeric(18,2),
  fees            numeric(18,2) default 0,
  slippage        numeric(18,5) default 0,
  r_multiple      numeric(8,4),
  execution_mode  text not null default 'paper',
  session         text,
  day_of_week     int,             -- 0=Monday
  hour_utc        int              -- 0-23
);

create index if not exists idx_trades_open_time on trades(open_time desc);
create index if not exists idx_trades_instrument on trades(instrument);
create index if not exists idx_trades_signal on trades(signal_id);

-- Auto-populate session/hour on insert
create or replace function trades_set_session_hour()
returns trigger language plpgsql as $$
begin
  new.hour_utc    := extract(hour from new.open_time at time zone 'UTC');
  new.day_of_week := extract(dow  from new.open_time at time zone 'UTC');
  return new;
end;
$$;

drop trigger if exists trg_trades_session on trades;
create trigger trg_trades_session
  before insert on trades
  for each row execute function trades_set_session_hour();

-- ── Commands ──────────────────────────────────────────────────────────────────
create table if not exists commands (
  id          uuid primary key default gen_random_uuid(),
  type        text not null,         -- PAUSE|RESUME|NEWS_LOCK|KILL|CLOSE_ALL
  payload     jsonb default '{}',
  created_by  uuid references auth.users(id),
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null default now() + interval '30 seconds',
  status      text not null default 'pending',  -- pending|done|failed|expired
  result      text,
  acked_at    timestamptz
);

create index if not exists idx_commands_status on commands(status, created_at);

-- ── Settings & history ────────────────────────────────────────────────────────
create table if not exists settings (
  key         text primary key,
  value       jsonb not null,
  updated_at  timestamptz not null default now(),
  updated_by  uuid references auth.users(id)
);

create table if not exists settings_history (
  id          bigserial primary key,
  key         text not null,
  old_value   jsonb,
  new_value   jsonb not null,
  changed_at  timestamptz not null default now(),
  changed_by  uuid references auth.users(id)
);

-- ── Logs ─────────────────────────────────────────────────────────────────────
create table if not exists logs (
  id           bigserial primary key,
  ts           timestamptz not null default now(),
  level        text not null,           -- DEBUG|INFO|WARNING|ERROR|CRITICAL
  code         text not null,
  message      text not null,
  context_json jsonb default '{}'
);

create index if not exists idx_logs_ts on logs(ts desc);
create index if not exists idx_logs_level on logs(level, ts desc);

-- ── Pre-aggregated analytics view ─────────────────────────────────────────────
create or replace view analytics_by_hour as
select
  instrument,
  day_of_week,
  hour_utc,
  count(*) filter (where pnl is not null)        as trade_count,
  avg(r_multiple)                                 as avg_r,
  sum(pnl)                                        as net_pnl,
  count(*) filter (where pnl > 0 and pnl is not null) as wins,
  count(*) filter (where pnl <= 0 and pnl is not null) as losses
from trades
group by instrument, day_of_week, hour_utc;

-- ── Row-Level Security ────────────────────────────────────────────────────────
alter table heartbeats        enable row level security;
alter table accounts_snapshot enable row level security;
alter table signals           enable row level security;
alter table evaluations       enable row level security;
alter table trades            enable row level security;
alter table commands          enable row level security;
alter table settings          enable row level security;
alter table settings_history  enable row level security;
alter table logs              enable row level security;

-- Owner role: full access to everything
create policy "owner_all" on heartbeats        for all using (auth.role() = 'authenticated');
create policy "owner_all" on accounts_snapshot for all using (auth.role() = 'authenticated');
create policy "owner_all" on signals           for all using (auth.role() = 'authenticated');
create policy "owner_all" on evaluations       for all using (auth.role() = 'authenticated');
create policy "owner_all" on trades            for all using (auth.role() = 'authenticated');
create policy "owner_all" on settings          for all using (auth.role() = 'authenticated');
create policy "owner_all" on settings_history  for all using (auth.role() = 'authenticated');
create policy "owner_all" on logs              for all using (auth.role() = 'authenticated');

-- Commands: only the owner who created a command can see it
create policy "owner_commands" on commands
  for all using (created_by = auth.uid() or auth.role() = 'service_role');

-- Service role (bot engine): full access via service_role key
-- (service_role bypasses RLS by default in Supabase)
