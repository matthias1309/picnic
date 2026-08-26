import { useNavigate } from "react-router-dom";
import { useDeleteReceipt, useReceiptDetail } from "../../hooks/useReceipts";
import { formatCents } from "../../lib/format";
import type { ReceiptItemOut } from "../../types";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

interface ReceiptDetailProps {
  receiptId: number;
}

interface OrderGroup {
  orderNumber: string | null;
  items: ReceiptItemOut[];
}

const ITEM_ROW_CLASSES = "grid grid-cols-[1fr_3rem_5rem_5rem] items-center gap-3 py-2.5 text-sm";

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
    <li className={ITEM_ROW_CLASSES}>
      <span className="truncate text-gray-900">{item.product_name}</span>
      <span className="text-right tabular-nums text-gray-500">{item.quantity}x</span>
      <span className="text-right tabular-nums text-gray-500">
        {formatCents(item.unit_price_cents)}
      </span>
      <span className="text-right font-medium tabular-nums text-gray-900">
        {formatCents(item.line_total_cents)}
      </span>
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
    <Card testId="receipt-detail">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            Kassenbon vom {new Date(data.effective_date).toLocaleDateString("de-DE")}
          </h2>
          <p className="mt-0.5 text-sm text-gray-500">{data.from_address}</p>
        </div>
        <Button variant="danger" onClick={handleDelete} disabled={deleteReceipt.isPending}>
          Kassenbon löschen
        </Button>
      </div>

      {groupItemsByOrder(data.items).map((group, groupIndex) => (
        <div
          key={group.orderNumber ?? `group-${groupIndex}`}
          className="mt-5"
          data-testid={group.orderNumber ? `order-group-${group.orderNumber}` : undefined}
        >
          {group.orderNumber && (
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Bestellnr {group.orderNumber}
            </h3>
          )}
          <ul className="divide-y divide-surface-border">
            {group.items.map((item, index) => (
              <ReceiptItemRow key={index} item={item} />
            ))}
          </ul>
        </div>
      ))}

      <p className="mt-5 border-t border-surface-border pt-4 text-right font-semibold tabular-nums text-gray-900">
        Gesamt: {formatCents(data.total_cents)}
      </p>
    </Card>
  );
}
