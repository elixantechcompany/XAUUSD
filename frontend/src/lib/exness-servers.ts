/**
 * Official Exness MT5 Server List
 * Complete list of all Demo (Trial) and Real servers for MT5 trading accounts.
 */

export const EXNESS_DEMO_SERVERS: string[] = [
  "Exness-MT5Trial",
  "Exness-MT5Trial2",
  "Exness-MT5Trial3",
  "Exness-MT5Trial4",
  "Exness-MT5Trial5",
  "Exness-MT5Trial6",
  "Exness-MT5Trial7",
  "Exness-MT5Trial8",
  "Exness-MT5Trial9",
  "Exness-MT5Trial10",
  "Exness-MT5Trial11",
  "Exness-MT5Trial12",
];

export const EXNESS_REAL_SERVERS: string[] = [
  "Exness-MT5Real",
  "Exness-MT5Real2",
  "Exness-MT5Real3",
  "Exness-MT5Real4",
  "Exness-MT5Real5",
  "Exness-MT5Real6",
  "Exness-MT5Real7",
  "Exness-MT5Real8",
  "Exness-MT5Real9",
  "Exness-MT5Real10",
  "Exness-MT5Real11",
  "Exness-MT5Real12",
  "Exness-MT5Real13",
  "Exness-MT5Real14",
  "Exness-MT5Real15",
  "Exness-MT5Real16",
  "Exness-MT5Real17",
  "Exness-MT5Real18",
  "Exness-MT5Real19",
  "Exness-MT5Real20",
  "Exness-MT5Real21",
  "Exness-MT5Real22",
  "Exness-MT5Real23",
  "Exness-MT5Real24",
  "Exness-MT5Real25",
];

export const ALL_EXNESS_SERVERS: string[] = [
  ...EXNESS_DEMO_SERVERS,
  ...EXNESS_REAL_SERVERS,
];

export function isDemoServer(server: string): boolean {
  const s = server.toLowerCase();
  return s.includes("trial") || s.includes("demo");
}
