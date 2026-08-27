import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson, putJson } from "../api/client";
import type { CategoryKey, ProductOut } from "../types";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => fetchJson<ProductOut[]>("/products"),
  });
}

export function useUpdateProductCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, categoryKey }: { productId: number; categoryKey: CategoryKey }) =>
      putJson<ProductOut>(`/products/${productId}/category`, { category_key: categoryKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}
