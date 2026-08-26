import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** Appended to the base surface classes, so callers can tint without forking. */
  className?: string;
  testId?: string;
}

/** The app's one content surface — every block sits on one of these. */
export function Card({ children, className = "", testId, ...nativeProps }: CardProps) {
  return (
    <div
      data-testid={testId}
      className={`rounded-card border border-surface-border bg-surface p-5 shadow-card ${className}`}
      {...nativeProps}
    >
      {children}
    </div>
  );
}
