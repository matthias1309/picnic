import { Button } from "../ui/Button";

interface ErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorMessage({
  message = "Etwas ist schiefgelaufen.",
  onRetry,
}: ErrorMessageProps) {
  return (
    <div
      role="alert"
      className="rounded-card border border-negative-600/20 bg-negative-50 p-4 text-sm text-negative-700"
    >
      <p>{message}</p>
      {onRetry && (
        <Button variant="danger" onClick={onRetry} className="mt-3">
          Erneut versuchen
        </Button>
      )}
    </div>
  );
}
