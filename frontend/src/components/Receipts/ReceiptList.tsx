import { Link } from "react-router-dom";
import { useReceipts } from "../../hooks/useReceipts";
import { useUiStore } from "../../store/useUiStore";
import { formatCents } from "../../lib/format";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

const PAGE_SIZE = 20;

export function ReceiptList() {
  const offset = useUiStore((state) => state.receiptsOffset);
  const setOffset = useUiStore((state) => state.setReceiptsOffset);
  const { data, isLoading, isError, refetch } = useReceipts(PAGE_SIZE, offset);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load receipts." onRetry={refetch} />;
  }

  if (data.items.length === 0) {
    return <EmptyState message="No receipts found." />;
  }

  const hasPrevious = offset > 0;
  const hasNext = offset + data.limit < data.total;

  return (
    <div>
      <ul data-testid="receipt-list" className="divide-y divide-gray-200">
        {data.items.map((receipt) => (
          <li key={receipt.id}>
            <Link
              to={`/receipts/${receipt.id}`}
              className="flex items-center justify-between py-2 hover:bg-gray-50"
            >
              <span>{new Date(receipt.effective_date).toLocaleDateString("de-DE")}</span>
              <span className="text-gray-500">{receipt.item_count} items</span>
              <span className="font-medium">{formatCents(receipt.total_cents)}</span>
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          disabled={!hasPrevious}
          className="rounded bg-gray-100 px-3 py-1 text-sm disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-500">
          {offset + 1}-{Math.min(offset + data.limit, data.total)} of {data.total}
        </span>
        <button
          type="button"
          onClick={() => setOffset(offset + PAGE_SIZE)}
          disabled={!hasNext}
          className="rounded bg-gray-100 px-3 py-1 text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
