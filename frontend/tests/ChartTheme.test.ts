import { describe, expect, it } from "vitest";
import { CATEGORY_COLORS } from "../src/lib/chart-theme";

/**
 * Chart theme tests (TEST-026).
 *
 * Traces: ARCH-026
 * Verifies: REQ-026 (AC-026-07)
 */

describe("CATEGORY_COLORS", () => {
  // TC-026-10
  // Given CATEGORY_COLORS from chart-theme.ts
  // Then it has an entry for grains, breakfast, baking, condiments, canned and snacks
  // And no two entries share a colour value (case-insensitive)
  it("should give every category its own colour", () => {
    // Arrange
    const newKeys = ["grains", "breakfast", "baking", "condiments", "canned", "snacks"] as const;

    // Act
    const colours = Object.values(CATEGORY_COLORS).map((colour) => colour.toLowerCase());

    // Assert
    newKeys.forEach((key) => expect(CATEGORY_COLORS[key]).toMatch(/^#[0-9a-f]{6}$/i));
    expect(new Set(colours).size).toBe(colours.length);
  });
});
