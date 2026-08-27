import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "../api/client";
import type { Category } from "../types";

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => fetchJson<Category[]>("/categories"),
    // The set is a backend constant, so it never changes within a session.
    staleTime: Infinity,
  });
}
