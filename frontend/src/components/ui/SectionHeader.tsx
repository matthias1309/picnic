import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  /** Controls rendered on the trailing edge, e.g. a toggle group. */
  action?: ReactNode;
}

export function SectionHeader({ title, action }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      {action}
    </div>
  );
}
