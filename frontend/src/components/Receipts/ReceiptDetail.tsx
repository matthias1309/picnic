import { useNavigate } from "react-router-dom";
import { useDeleteReceipt, useReceiptDetail } from "../../hooks/useReceipts";
import { formatCents } from "../../lib/format";
import type { ReceiptItemOut } from "../../types";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

interface ReceiptDetailProps {
  receiptId: number;
}

interface OrderGroup {
  orderNumber: string | null;
  items: ReceiptItemOut[];
}

function groupItemsByOrder(items: ReceiptItemOut[]): OrderGroup[] {
  const groups: OrderGroup[] = [];
  for (const item of items) {
    const current = groups[groups.length - 1];
    if (current && current.orderNumber === item.order_number) {
      current.items.push(item);
    } else {
      groups.push({ orderNumber: item.order_number, items: [item] });
    }
  }
  return groups;
}

function ReceiptItemRow({ item }: { item: ReceiptItemOut }) {
  return (
    <li className="flex items-center justify-between py-2">
      <span>{item.product_name}</span>
      <span className="text-gray-500">{item.quantity}x</span>
      <span className="text-gray-500">{formatCents(item.unit_price_cents)}</span>
      <span className="font-medium">{formatCents(item.line_total_cents)}</span>
    </li>
  );
}

export function ReceiptDetail({ receiptId }: ReceiptDetailProps) {
  const { data, isLoading, isError, refetch } = useReceiptDetail(receiptId);
  const deleteReceipt = useDeleteReceipt();
  const navigate = useNavigate();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Kassenbon konnte nicht geladen werden." onRetry={refetch} />;
  }

  const handleDelete = () => {
    if (!window.confirm("Diesen Kassenbon löschen? Das kann nicht rückgängig gemacht werden.")) {
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
          Kassenbon vom {new Date(data.effective_date).toLocaleDateString("de-DE")}
        </h2>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleteReceipt.isPending}
          className="rounded bg-red-50 px-3 py-1 text-sm text-red-600 hover:bg-red-100 disabled:opacity-50"
        >
          Kassenbon löschen
        </button>
      </div>
      <p className="text-sm text-gray-500">{data.from_address}</p>
      {groupItemsByOrder(data.items).map((group, groupIndex) => (
        <div
          key={group.orderNumber ?? `group-${groupIndex}`}
          className="mt-4"
          data-testid={group.orderNumber ? `order-group-${group.orderNumber}` : undefined}
        >
          {group.orderNumber && (
            <h3 className="text-sm font-semibold text-gray-700">Bestellnr {group.orderNumber}</h3>
          )}
          <ul className="divide-y divide-gray-200">
            {group.items.map((item, index) => (
              <ReceiptItemRow key={index} item={item} />
            ))}
          </ul>
        </div>
      ))}
      <p className="mt-4 text-right font-semibold">Gesamt: {formatCents(data.total_cents)}</p>
    </div>
  );
}
