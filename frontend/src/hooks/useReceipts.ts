import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteJson, fetchJson } from "../api/client";
import type { PaginatedReceipts, ReceiptDetail } from "../types";

export function useReceipts(limit: number, offset: number) {
  return useQuery({
    queryKey: ["receipts", limit, offset],
    queryFn: () => fetchJson<PaginatedReceipts>("/receipts", { limit, offset }),
  });
}

export function useReceiptDetail(receiptId: number | null) {
  return useQuery({
    queryKey: ["receipts", receiptId],
    queryFn: () => fetchJson<ReceiptDetail>(`/receipts/${receiptId}`),
    enabled: receiptId !== null,
  });
}

export function useDeleteReceipt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (receiptId: number) => deleteJson(`/receipts/${receiptId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
    },
  });
}
