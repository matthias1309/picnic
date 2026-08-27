import { CategorySpending } from "../components/Charts/CategorySpending";
import { PriceHistory } from "../components/Charts/PriceHistory";
import { PurchaseStats } from "../components/Charts/PurchaseStats";

export function Stats() {
  return (
    <div className="space-y-8">
      <PurchaseStats />
      <CategorySpending />
      <PriceHistory />
    </div>
  );
}
