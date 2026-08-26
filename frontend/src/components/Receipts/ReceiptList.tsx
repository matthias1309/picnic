import { Link } from "react-router-dom";
import { useReceipts } from "../../hooks/useReceipts";
import { useUiStore } from "../../store/useUiStore";
import { formatCents } from "../../lib/format";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";

const PAGE_SIZE = 20;

export function ReceiptList() {
  const offset = useUiStore((state) => state.receiptsOffset);
  const setOffset = useUiStore((state) => state.setReceiptsOffset);
  const { data, isLoading, isError, refetch } = useReceipts(PAGE_SIZE, offset);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Kassenbons konnten nicht geladen werden." onRetry={refetch} />;
  }

  if (data.items.length === 0) {
    return <EmptyState message="Keine Kassenbons gefunden." />;
  }

  const hasPrevious = offset > 0;
  const hasNext = offset + data.limit < data.total;

  return (
    <Card>
      <SectionHeader title="Kassenbons" />
      <ul data-testid="receipt-list" className="divide-y divide-surface-border">
        {data.items.map((receipt) => (
          <li key={receipt.id}>
            <Link
              to={`/receipts/${receipt.id}`}
              className="grid grid-cols-[1fr_auto_auto] items-center gap-4 rounded-lg px-2 py-3 text-sm transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <span className="font-medium text-gray-900">
                {new Date(receipt.effective_date).toLocaleDateString("de-DE")}
              </span>
              <span className="w-24 text-right tabular-nums text-gray-500">
                {receipt.item_count} Artikel
              </span>
              <span className="w-24 text-right font-medium tabular-nums text-gray-900">
                {formatCents(receipt.total_cents)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex items-center justify-between gap-3 border-t border-surface-border pt-4">
        <Button
          variant="secondary"
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          disabled={!hasPrevious}
        >
          Zurück
        </Button>
        <span className="text-sm tabular-nums text-gray-500">
          {offset + 1}–{Math.min(offset + data.limit, data.total)} von {data.total}
        </span>
        <Button
          variant="secondary"
          onClick={() => setOffset(offset + PAGE_SIZE)}
          disabled={!hasNext}
        >
          Weiter
        </Button>
      </div>
    </Card>
  );
}
