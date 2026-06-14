interface ErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message = "Something went wrong.", onRetry }: ErrorMessageProps) {
  return (
    <div role="alert" className="rounded-md bg-red-50 p-4 text-red-700">
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700"
        >
          Retry
        </button>
      )}
    </div>
  );
}
