interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return <p className="py-8 text-center text-gray-500">{message}</p>;
}
