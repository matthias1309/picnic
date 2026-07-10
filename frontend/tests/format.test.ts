import { describe, expect, it } from "vitest";
import { getPastMonths } from "../src/lib/format";

describe("getPastMonths", () => {
  // TC-017-01
  // Given today is 2026-07-10
  // When getPastMonths(12, today) is called
  // Then it returns 12 months, most recent first, starting with "2026-06" and ending with "2025-07"
  it("returns the 12 months preceding today, most recent first", () => {
    // Arrange
    const today = new Date(2026, 6, 10); // 2026-07-10

    // Act
    const months = getPastMonths(12, today);

    // Assert
    expect(months).toHaveLength(12);
    expect(months[0]).toBe("2026-06");
    expect(months[11]).toBe("2025-07");
  });

  it("handles the year boundary correctly", () => {
    // Arrange
    const today = new Date(2026, 0, 15); // 2026-01-15

    // Act
    const months = getPastMonths(3, today);

    // Assert
    expect(months).toEqual(["2025-12", "2025-11", "2025-10"]);
  });
});
