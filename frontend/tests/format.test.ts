import { describe, expect, it } from "vitest";
import { formatMonth, getPastMonths } from "../src/lib/format";

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

describe("formatMonth", () => {
  // TC-020-01
  // Given the API month key "2026-08"
  // When formatMonth is called
  // Then it returns "August 2026"
  it("formats an API month key as a German month name and year", () => {
    // Arrange
    const month = "2026-08";

    // Act
    const formatted = formatMonth(month);

    // Assert
    expect(formatted).toBe("August 2026");
  });

  it("formats a month whose German and English names differ", () => {
    expect(formatMonth("2026-01")).toBe("Januar 2026");
  });

  it("formats a December key without slipping into the next year", () => {
    expect(formatMonth("2025-12")).toBe("Dezember 2025");
  });
});
