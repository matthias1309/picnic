import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700",
  secondary: "border border-surface-border bg-surface text-gray-700 hover:bg-surface-muted",
  ghost: "text-gray-600 hover:bg-surface-muted hover:text-gray-900",
  danger: "bg-negative-50 text-negative-700 hover:bg-negative-600 hover:text-white",
};

const BASE_CLASSES =
  "inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium " +
  "transition-colors focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-brand-500 focus-visible:ring-offset-1 disabled:opacity-50";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

/** The app's only button. Native props are forwarded, so callers keep type/disabled/aria. */
export function Button({
  variant = "primary",
  className = "",
  type = "button",
  children,
  ...nativeProps
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${BASE_CLASSES} ${VARIANT_CLASSES[variant]} ${className}`}
      {...nativeProps}
    >
      {children}
    </button>
  );
}
