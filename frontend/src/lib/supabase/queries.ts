/**
 * Data-access layer — all Supabase queries in one place.
 * Every function returns typed data or throws.
 * Never fabricates data.
 */
import { getSupabaseClient } from "./client";
import type {
  Heartbeat, AccountSnapshot, Signal, Trade,
  Command, LogEntry, AnalyticsByHour,
  Instrument, SignalStatus, CommandType,
} from "./types";

// ── Heartbeat ─────────────────────────────────────────────────────────────────

export async function getLatestHeartbeat(): Promise<Heartbeat | null> {
  const { data, error } = await getSupabaseClient()
    .from("heartbeats")
    .select("*")
    .order("ts", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export function subscribeToHeartbeat(cb: (h: Heartbeat) => void) {
  return getSupabaseClient()
    .channel("heartbeats")
    .on("postgres_changes", { event: "INSERT", schema: "public", table: "heartbeats" },
      (payload) => cb(payload.new as Heartbeat))
    .subscribe();
}

// ── Account ───────────────────────────────────────────────────────────────────

export async function getLatestAccountSnapshot(): Promise<AccountSnapshot | null> {
  const { data, error } = await getSupabaseClient()
    .from("accounts_snapshot")
    .select("*")
    .order("ts", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export async function getAccountHistory(hours = 24): Promise<AccountSnapshot[]> {
  const since = new Date(Date.now() - hours * 3600_000).toISOString();
  const { data, error } = await getSupabaseClient()
    .from("accounts_snapshot")
    .select("*")
    .gte("ts", since)
    .order("ts", { ascending: true });
  if (error) throw error;
  return data ?? [];
}

// ── Signals ───────────────────────────────────────────────────────────────────

export async function getSignals(filters?: {
  instrument?: Instrument;
  status?: SignalStatus;
  limit?: number;
}): Promise<Signal[]> {
  let q = getSupabaseClient()
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(filters?.limit ?? 50);
  if (filters?.instrument) q = q.eq("instrument", filters.instrument);
  if (filters?.status)     q = q.eq("status", filters.status);
  const { data, error } = await q;
  if (error) throw error;
  return data ?? [];
}

export async function getSignalById(id: string): Promise<Signal | null> {
  const { data, error } = await getSupabaseClient()
    .from("signals")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export function subscribeToSignals(cb: (s: Signal) => void) {
  return getSupabaseClient()
    .channel("signals")
    .on("postgres_changes", { event: "*", schema: "public", table: "signals" },
      (payload) => cb(payload.new as Signal))
    .subscribe();
}

// ── Trades ────────────────────────────────────────────────────────────────────

export async function getTrades(filters?: {
  instrument?: Instrument;
  open_only?: boolean;
  limit?: number;
}): Promise<Trade[]> {
  let q = getSupabaseClient()
    .from("trades")
    .select("*")
    .order("open_time", { ascending: false })
    .limit(filters?.limit ?? 100);
  if (filters?.instrument) q = q.eq("instrument", filters.instrument);
  if (filters?.open_only)  q = q.is("close_time", null);
  const { data, error } = await q;
  if (error) throw error;
  return data ?? [];
}

// ── Commands ──────────────────────────────────────────────────────────────────

export async function sendCommand(
  type: CommandType,
  payload: Record<string, unknown> = {}
): Promise<Command> {
  const { data, error } = await getSupabaseClient()
    .from("commands")
    .insert({ type, payload, status: "pending" })
    .select()
    .single();
  if (error) throw error;
  return data;
}

export async function getRecentCommands(limit = 20): Promise<Command[]> {
  const { data, error } = await getSupabaseClient()
    .from("commands")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}

export function subscribeToCommandUpdates(cb: (c: Command) => void) {
  return getSupabaseClient()
    .channel("commands")
    .on("postgres_changes", { event: "UPDATE", schema: "public", table: "commands" },
      (payload) => cb(payload.new as Command))
    .subscribe();
}

// ── Logs ──────────────────────────────────────────────────────────────────────

export async function getLogs(filters?: {
  level?: string;
  limit?: number;
}): Promise<LogEntry[]> {
  let q = getSupabaseClient()
    .from("logs")
    .select("*")
    .order("ts", { ascending: false })
    .limit(filters?.limit ?? 100);
  if (filters?.level) q = q.eq("level", filters.level);
  const { data, error } = await q;
  if (error) throw error;
  return data ?? [];
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export async function getAnalyticsByHour(): Promise<AnalyticsByHour[]> {
  const { data, error } = await getSupabaseClient()
    .from("analytics_by_hour")
    .select("*");
  if (error) throw error;
  return data ?? [];
}
