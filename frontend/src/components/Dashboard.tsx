import { useSummary } from "../hooks/useStats";
import { formatCents } from "../lib/format";
import { ErrorMessage } from "./common/ErrorMessage";
import { LoadingSpinner } from "./common/LoadingSpinner";

export function Dashboard() {
  const { data, isLoading, isError, refetch } = useSummary();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load summary statistics." onRetry={refetch} />;
  }

  const cards = [
    { label: "Total spend", value: formatCents(data.total_spend_cents) },
    { label: "Receipts", value: data.receipt_count.toLocaleString("de-DE") },
    { label: "Distinct products", value: data.distinct_product_count.toLocaleString("de-DE") },
    { label: "Average basket", value: formatCents(data.average_basket_cents) },
    { label: "This month's spend", value: formatCents(data.current_month_spend_cents) },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg bg-white p-4 shadow">
          <p className="text-sm text-gray-500">{card.label}</p>
          <p className="text-2xl font-semibold">{card.value}</p>
        </div>
      ))}
    </div>
  );
}
