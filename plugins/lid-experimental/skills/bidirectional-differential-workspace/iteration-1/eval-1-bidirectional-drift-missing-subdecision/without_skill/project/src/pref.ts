// @spec PREF-001
export function renderItems(items: Array<{ primary?: string; secondary?: string }>): string[] {
  const out: string[] = [];
  for (const item of items) {
    const text = item.primary || item.secondary || '';
    if (!text) continue;
    out.push(text);
  }
  return out;
}
