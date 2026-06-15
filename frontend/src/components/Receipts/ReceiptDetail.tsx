import { useNavigate } from "react-router-dom";
import { useDeleteReceipt, useReceiptDetail } from "../../hooks/useReceipts";
import { formatCents } from "../../lib/format";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

interface ReceiptDetailProps {
  receiptId: number;
}

export function ReceiptDetail({ receiptId }: ReceiptDetailProps) {
  const { data, isLoading, isError, refetch } = useReceiptDetail(receiptId);
  const deleteReceipt = useDeleteReceipt();
  const navigate = useNavigate();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load receipt." onRetry={refetch} />;
  }

  const handleDelete = () => {
    if (!window.confirm("Delete this receipt? This cannot be undone.")) {
      return;
    }
    deleteReceipt.mutate(receiptId, {
      onSuccess: () => navigate("/receipts"),
    });
  };

  return (
    <div data-testid="receipt-detail">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Receipt from {new Date(data.received_date).toLocaleDateString("de-DE")}
        </h2>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleteReceipt.isPending}
          className="rounded bg-red-50 px-3 py-1 text-sm text-red-600 hover:bg-red-100 disabled:opacity-50"
        >
          Delete receipt
        </button>
      </div>
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
