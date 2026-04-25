// @spec SCORE-001
export function scorePair(x: Item, y: Item): number {
  const aOk = predicateA(x, y);
  const bOk = predicateB(x, y);
  if (aOk && bOk) return 3;
  if (aOk && !bOk) return 2;
  if (!aOk && bOk) return 1;
  return 0;
}

type Item = { id: string };
function predicateA(x: Item, y: Item): boolean { return x.id.length > y.id.length; }
function predicateB(x: Item, y: Item): boolean { return x.id < y.id; }
