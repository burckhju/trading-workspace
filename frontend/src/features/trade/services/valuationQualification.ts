/** Display the owner's qualified result; never infer execution currency in the UI. */
export function qualifiedUnrealizedPnl(
  value: string | null,
  usable: boolean | undefined,
  currency: string | null,
): string | null {
  return usable === true && currency ? value : null;
}

export function unrealizedPnlReason(reason: string | undefined): string {
  switch (reason) {
    case 'COST_BASIS_CURRENCY_UNKNOWN':
      return 'Die Kaufwährung ist für mindestens einen wirksamen Kauf der Kostenbasis nicht belegt. Gewinn/Verlust ist nicht berechenbar.';
    case 'COST_BASIS_CURRENCY_MIXED':
      return 'Die Kostenbasis enthält unterschiedliche Kaufwährungen. Gewinn/Verlust ist nicht berechenbar.';
    case 'COST_BASIS_CURRENCY_MISMATCH':
      return 'Die belegte Kaufwährung der Kostenbasis stimmt nicht mit der Kurswährung überein. Gewinn/Verlust ist nicht berechenbar.';
    case 'WARRANT_QUOTE_STALE':
      return 'Der Produktkurs ist für einen aktuellen Gewinn/Verlust zu alt.';
    case 'WARRANT_QUOTE_MISSING':
    case 'WARRANT_BID_MISSING':
    case 'NO_USABLE_WARRANT_QUOTE':
      return 'Für den Gewinn/Verlust liegt kein verwendbarer Produktkurs vor.';
    default:
      return 'Gewinn/Verlust ist auf dieser Datengrundlage nicht berechenbar.';
  }
}
