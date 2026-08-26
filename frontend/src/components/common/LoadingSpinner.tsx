export function LoadingSpinner() {
  return (
    <div role="status" aria-label="Lädt" className="flex justify-center py-8">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-gray-600" />
    </div>
  );
}
