/** Classify AHJ fee lines so estimators do not mix permit vs tap vs impact. */

export type FeeKind = 'permit' | 'tap / connection' | 'impact' | 'other — confirm AHJ';

export function classifyFeeKind(label = '', detail = '', trade = ''): FeeKind {
  const t = `${label} ${detail} ${trade}`.toLowerCase();
  if (
    /impact fee|impact fees|roadway impact|park impact|pro rata|pro-rata|capital recovery/.test(t)
  ) {
    return 'impact';
  }
  if (
    /tap fee|water tap|sewer tap|meter |connection fee|water connection|wastewater connection|service connection/.test(
      t
    )
  ) {
    return 'tap / connection';
  }
  if (
    /permit|plan review|building fee|inspection fee|electrical permit|mechanical permit|plumbing permit/.test(
      t
    )
  ) {
    return 'permit';
  }
  return 'other — confirm AHJ';
}

export function feeKindHint(kind: FeeKind): string {
  switch (kind) {
    case 'permit':
      return 'Permit / review — not a tap or impact fee';
    case 'tap / connection':
      return 'Utility tap / connection — not the building permit';
    case 'impact':
      return 'Impact / capacity — often larger than the permit';
    default:
      return 'Unlabeled — confirm kind on the official schedule';
  }
}
