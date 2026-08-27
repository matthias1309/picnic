interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return <p className="py-10 text-center text-sm text-gray-500">{message}</p>;
}
