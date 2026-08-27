export function LoadingSpinner() {
  return (
    <div role="status" aria-label="Lädt" className="flex justify-center py-10">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-surface-border border-t-brand-600" />
    </div>
  );
}
