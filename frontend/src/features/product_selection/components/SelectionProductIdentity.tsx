import type { WarrantResponse } from '../../product/types/api';

export function SelectionProductIdentity({
  productId,
  product,
  loading,
  heading = false,
}: {
  productId: string;
  product?: WarrantResponse;
  loading: boolean;
  heading?: boolean;
}) {
  // Never fall back to another candidate, the plan's underlying or the first catalogue item.
  const resolved = product?.id === productId ? product : undefined;
  const Title = heading ? 'h3' : 'p';
  return (
    <div className="min-w-0">
      <Title className="mt-1 break-words font-semibold">
        {resolved?.display_name ||
          (loading ? 'Produktname wird geladen …' : 'Produktname nicht verfügbar')}
      </Title>
      <p className="mt-1 break-words text-sm text-slate-400">
        WKN {resolved?.wkn ?? 'nicht hinterlegt'} · ISIN {resolved?.isin ?? 'nicht hinterlegt'}
      </p>
      <details className="mt-2 text-xs text-slate-500">
        <summary className="cursor-pointer">Technische Produkt-ID</summary>
        <p className="mt-1 break-all">{productId}</p>
      </details>
    </div>
  );
}
