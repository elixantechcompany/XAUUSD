/**
 * Supabase Database types — aligned with docs/supabase_schema.sql
 *
 * These are hand-written to match the schema exactly.
 * Run `supabase gen types typescript` after connecting to auto-generate.
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]
  | Record<string, unknown>;

export type SetupState =
  | "FVG_DETECTED"
  | "SWEEP_CONFIRMED"
  | "WAITING_FOR_RETRACEMENT"
  | "REFERENCE_CANDLE_SAVED"
  | "WAITING_FOR_GAP_EXIT"
  | "GAP_EXITED"
  | "WAITING_FOR_TRIGGER"
  | "SIGNAL_READY"
  | "RISK_CHECK"
  | "ORDER_PENDING"
  | "POSITION_OPEN"
  | "CLOSED"
  | "EXPIRED"
  | "INVALIDATED"
  | "REJECTED";

export type SignalStatus =
  | "new"
  | "taken"
  | "skipped"
  | "expired"
  | "cancelled"
  | "hit_tp_or_sl";

export type Direction = "BULLISH" | "BEARISH";
export type Instrument = "XAUUSD" | "BTCUSD";
export type ExecutionMode = "paper" | "demo";
export type Session = "Asia" | "London" | "NewYork" | "Overlap";
export type QualityGrade = "A" | "B" | "C";
export type CommandType =
  | "PAUSE"
  | "RESUME"
  | "NEWS_LOCK"
  | "KILL"
  | "CLOSE_ALL"
  | "RESTART"
  | "REGISTER_CHILD_ACCOUNT"
  | "CONFIGURE_MASTER"
  | "EXECUTE_TRADE"
  | "CLOSE_TRADE";
export type CommandStatus = "pending" | "done" | "failed" | "expired";

export interface Heartbeat {
  id: number;
  ts: string;
  mt5_connected: boolean;
  last_tick_ts: string | null;
  equity: number | null;
  balance: number | null;
  execution_mode: ExecutionMode;
  live_trading_enabled: false;
}

export interface AccountSnapshot {
  id: number;
  ts: string;
  equity: number | null;
  balance: number | null;
  daily_pnl: number | null;
  drawdown_pct: number | null;
  open_positions_count: number;
  open_positions?: number;   // alias used in overview page
  execution_mode: ExecutionMode;
}

export interface Signal {
  id: string;
  created_at: string;
  updated_at: string;
  instrument: Instrument;
  timeframe: string;
  direction: Direction;
  state: SetupState;
  status: SignalStatus;
  fvg_low: number | null;
  fvg_high: number | null;
  sweep_level: number | null;
  sweep_extreme: number | null;
  ref_candle_high: number | null;
  ref_candle_low: number | null;
  trigger_level: number | null;
  entry: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  suggested_lot_size: number | null;
  estimated_risk_usd: number | null;
  rr_ratio: number | null;
  rejection_reason: string | null;
  session: Session | null;
  quality_grade: QualityGrade | null;
  clarity_score?: number | null;
  clarity_grade?: string | null;
  positions_permitted?: number | null;
  tp1_structural?: number | null;
  tp2_structural?: number | null;
  h4_trend?: string | null;
  strategy_version: string;
  outcome: "win" | "loss" | "breakeven" | null;
  closed_at: string | null;
  r_multiple: number | null;
}

export interface Trade {
  ticket: string;
  signal_id: string | null;
  source: "bot" | "manual" | "paper";
  instrument: Instrument;
  side: Direction;
  lots: number;
  open_time: string;
  open_price: number;
  sl: number | null;
  tp: number | null;
  close_time: string | null;
  close_price: number | null;
  pnl: number | null;
  fees: number;
  slippage: number;
  r_multiple: number | null;
  execution_mode: ExecutionMode;
  session: Session | null;
  day_of_week: number | null;
  hour_utc: number | null;
}

export interface Command {
  id: string;
  type: CommandType;
  payload: Json;
  created_by?: string | null;
  created_at: string;
  expires_at?: string | null;   // nullable — optimistic local commands don't have this
  status: CommandStatus;
  result: string | null;
  acked_at?: string | null;
}

export interface LogEntry {
  id: number;
  ts: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  code: string;
  message: string;
  context_json: Json;
}

export interface SettingRow {
  key: string;
  value: Record<string, unknown>;
  updated_at?: string;
}

export interface AnalyticsByHour {
  instrument: Instrument;
  day_of_week: number;
  hour_utc: number;
  trade_count: number;
  avg_r: number | null;
  net_pnl: number | null;
  wins: number;
  losses: number;
}

// Minimal Database interface for createBrowserClient typing
export interface Database {
  public: {
    Tables: {
      heartbeats: { Row: Heartbeat; Insert: Omit<Heartbeat, "id">; Update: Partial<Heartbeat>; Relationships: [] };
      accounts_snapshot: { Row: AccountSnapshot; Insert: Omit<AccountSnapshot, "id">; Update: Partial<AccountSnapshot>; Relationships: [] };
      signals: { Row: Signal; Insert: Signal; Update: Partial<Signal>; Relationships: [] };
      trades: { Row: Trade; Insert: Trade; Update: Partial<Trade>; Relationships: [] };
      commands: { Row: Command; Insert: Partial<Command> & { type: CommandType; status: CommandStatus }; Update: Partial<Command>; Relationships: [] };
      logs: { Row: LogEntry; Insert: Omit<LogEntry, "id">; Update: never; Relationships: [] };
      settings: { Row: SettingRow; Insert: SettingRow; Update: Partial<SettingRow>; Relationships: [] };
    };
    Views: {
      analytics_by_hour: { Row: AnalyticsByHour; Relationships: [] };
    };
    Functions: Record<string, never>;
    Enums: Record<string, never>;
  };
}
