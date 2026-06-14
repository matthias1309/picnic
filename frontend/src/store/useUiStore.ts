import { create } from "zustand";
import type { PriceHistoryRange, SpendingGranularity } from "../types";

interface UiState {
  statsPeriod: SpendingGranularity;
  setStatsPeriod: (period: SpendingGranularity) => void;

  priceHistoryRange: PriceHistoryRange;
  setPriceHistoryRange: (range: PriceHistoryRange) => void;

  selectedProductId: number | null;
  setSelectedProductId: (productId: number | null) => void;

  receiptsOffset: number;
  setReceiptsOffset: (offset: number) => void;
}

export const useUiStore = create<UiState>((set) => ({
  statsPeriod: "month",
  setStatsPeriod: (period) => set({ statsPeriod: period }),

  priceHistoryRange: "6m",
  setPriceHistoryRange: (range) => set({ priceHistoryRange: range }),

  selectedProductId: null,
  setSelectedProductId: (productId) => set({ selectedProductId: productId }),

  receiptsOffset: 0,
  setReceiptsOffset: (offset) => set({ receiptsOffset: offset }),
}));
