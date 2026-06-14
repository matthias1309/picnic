import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "../api/client";
import type { ProductOut } from "../types";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => fetchJson<ProductOut[]>("/products"),
  });
}
