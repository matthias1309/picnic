import { describe, expect, it } from "vitest";
import { resolveApiBase } from "../src/api/client";
import { resolveBasePath } from "../config/basePath";

// Traces: ARCH-019
// Verifies: REQ-019 (AC-019-03, AC-019-04)

describe("resolveBasePath / resolveApiBase", () => {
  // TC-019-03
  // Given VITE_BASE_PATH="/" and VITE_API_BASE="/api" in the env object
  // When resolveBasePath(env) and resolveApiBase(env) are called
  // Then resolveBasePath returns "/" and resolveApiBase returns "/api"
  it("resolves root-relative values when the prod env vars are set", () => {
    // Arrange
    const env = { VITE_BASE_PATH: "/", VITE_API_BASE: "/api" };

    // Act
    const basePath = resolveBasePath(env);
    const apiBase = resolveApiBase(env);

    // Assert
    expect(basePath).toBe("/");
    expect(apiBase).toBe("/api");
  });

  // TC-019-04
  // Given an empty env object (VITE_BASE_PATH and VITE_API_BASE both unset)
  // When resolveBasePath(env) and resolveApiBase(env) are called
  // Then resolveBasePath returns "/picnic-frontend/" and resolveApiBase
  //   returns "/picnic/api" — today's hardcoded values, unchanged
  it("falls back to today's dev defaults when unset", () => {
    // Arrange
    const env = {};

    // Act
    const basePath = resolveBasePath(env);
    const apiBase = resolveApiBase(env);

    // Assert
    expect(basePath).toBe("/picnic-frontend/");
    expect(apiBase).toBe("/picnic/api");
  });
});
