import { BudgetWidget } from "../components/Budget/BudgetWidget";
import { Dashboard } from "../components/Dashboard";

export function Home() {
  return (
    <div className="space-y-6">
      <Dashboard />
      <BudgetWidget />
    </div>
  );
}
