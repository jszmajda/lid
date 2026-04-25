// @spec DEDUP-001
export function uniqueIds(ids: readonly string[]): string[] {
  if (ids.length === 0) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of ids) {
    if (!seen.has(id)) {
      seen.add(id);
      out.push(id);
    }
  }
  return out;
}
