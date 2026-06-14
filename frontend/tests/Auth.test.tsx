import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import * as apiClient from "../src/api/client";
import { LogoutButton } from "../src/App";
import { ProtectedRoute } from "../src/components/ProtectedRoute";
import { Login } from "../src/pages/Login";
import type { User } from "../src/types";
import { renderWithProviders } from "./test-utils";

const ALICE: User = { id: 1, username: "alice" };

function renderProtected() {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <div>Protected Content</div>
          </ProtectedRoute>
        }
      />
    </Routes>,
    { route: "/" },
  );
}

describe("ProtectedRoute", () => {
  // TC-006-09
  // Given GET /picnic/api/auth/me responds with 401 (not authenticated)
  // When the app renders a protected route ("/") inside <ProtectedRoute>
  // Then the user is redirected to "/login"
  // And the Login page (username/password form) is shown
  it("redirects unauthenticated users to /login", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockRejectedValue(
      new apiClient.ApiError("Not authenticated", 401),
    );

    // Act
    renderProtected();

    // Assert
    expect(
      await screen.findByRole("heading", { name: /picnic expense tracker/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /username/i })).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  // TC-006-10 (part 1)
  // Given GET /picnic/api/auth/me responds with 200 {"id": 1, "username": "alice"}
  // When the app renders a protected route ("/") inside <ProtectedRoute>
  // Then the wrapped page content is shown (no redirect to "/login")
  it("renders the protected content for authenticated users", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(ALICE);

    // Act
    renderProtected();

    // Assert
    expect(await screen.findByText("Protected Content")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /picnic expense tracker/i }),
    ).not.toBeInTheDocument();
  });
});

describe("LogoutButton", () => {
  // TC-006-10 (part 2)
  // When the user clicks the "Logout" control
  // Then POST /picnic/api/auth/logout is called
  // And the user is redirected to "/login"
  it("logs out and redirects to /login", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockRejectedValue(
      new apiClient.ApiError("Not authenticated", 401),
    );
    vi.spyOn(apiClient, "postJson").mockResolvedValue({ ok: true });

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<LogoutButton />} />
      </Routes>,
      { route: "/" },
    );

    // Act
    await userEvent.click(screen.getByRole("button", { name: /logout/i }));

    // Assert
    await waitFor(() => expect(apiClient.postJson).toHaveBeenCalledWith("/auth/logout", {}));
    expect(
      await screen.findByRole("heading", { name: /picnic expense tracker/i }),
    ).toBeInTheDocument();
  });
});
