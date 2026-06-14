import { useReceiptDetail } from "../../hooks/useReceipts";
import { formatCents } from "../../lib/format";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

interface ReceiptDetailProps {
  receiptId: number;
}

export function ReceiptDetail({ receiptId }: ReceiptDetailProps) {
  const { data, isLoading, isError, refetch } = useReceiptDetail(receiptId);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load receipt." onRetry={refetch} />;
  }

  return (
    <div data-testid="receipt-detail">
      <h2 className="text-lg font-semibold">
        Receipt from {new Date(data.received_date).toLocaleDateString("de-DE")}
      </h2>
      <p className="text-sm text-gray-500">{data.from_address}</p>
      <ul className="mt-4 divide-y divide-gray-200">
        {data.items.map((item, index) => (
          <li key={index} className="flex items-center justify-between py-2">
            <span>{item.product_name}</span>
            <span className="text-gray-500">{item.quantity}x</span>
            <span className="text-gray-500">{formatCents(item.unit_price_cents)}</span>
            <span className="font-medium">{formatCents(item.line_total_cents)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-right font-semibold">Total: {formatCents(data.total_cents)}</p>
    </div>
  );
}
