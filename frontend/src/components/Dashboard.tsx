import { useSummary } from "../hooks/useStats";
import { formatCents } from "../lib/format";
import { ErrorMessage } from "./common/ErrorMessage";
import { LoadingSpinner } from "./common/LoadingSpinner";
import { Card } from "./ui/Card";

export function Dashboard() {
  const { data, isLoading, isError, refetch } = useSummary();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return (
      <ErrorMessage message="Zusammenfassung konnte nicht geladen werden." onRetry={refetch} />
    );
  }

  const cards = [
    { label: "Gesamtausgaben", value: formatCents(data.total_spend_cents) },
    { label: "Kassenbons", value: data.receipt_count.toLocaleString("de-DE") },
    {
      label: "Verschiedene Artikel",
      value: data.distinct_product_count.toLocaleString("de-DE"),
    },
    { label: "Durchschnittlicher Einkauf", value: formatCents(data.average_basket_cents) },
    { label: "Ausgaben diesen Monat", value: formatCents(data.current_month_spend_cents) },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.label}>
          <p className="text-sm text-gray-500">{card.label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-gray-900">{card.value}</p>
        </Card>
      ))}
    </div>
  );
}
