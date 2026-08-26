import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import * as apiClient from "../src/api/client";
import { App, LogoutButton } from "../src/App";
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
      await screen.findByRole("heading", { name: /picnic ausgaben-tracker/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /benutzername/i })).toBeInTheDocument();
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
      screen.queryByRole("heading", { name: /picnic ausgaben-tracker/i }),
    ).not.toBeInTheDocument();
  });
});

describe("LogoutButton", () => {
  // TC-006-10 (part 2)
  // When the user clicks the "Abmelden" control
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
    await userEvent.click(screen.getByRole("button", { name: /abmelden/i }));

    // Assert
    await waitFor(() => expect(apiClient.postJson).toHaveBeenCalledWith("/auth/logout", {}));
    expect(
      await screen.findByRole("heading", { name: /picnic ausgaben-tracker/i }),
    ).toBeInTheDocument();
  });
});

describe("German UI shell", () => {
  // TC-020-02
  // Given the user is logged in and the app shell is rendered
  // When the header is inspected
  // Then links named "Übersicht", "Statistiken" and "Kassenbons" are present
  // And a button named "Abmelden" is present
  it("labels the navigation and session controls in German", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/auth/me") return Promise.resolve(ALICE);
      return Promise.reject(new apiClient.ApiError("not used in this test", 500));
    });

    // Act
    renderWithProviders(<App />, { route: "/" });

    // Assert
    expect(await screen.findByRole("link", { name: "Übersicht" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Statistiken" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kassenbons" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Abmelden" })).toBeInTheDocument();

    expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Stats" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Receipts" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Logout" })).not.toBeInTheDocument();
  });

  // TC-020-03
  // Given the user is not logged in
  // When the login screen renders
  // Then its fields, submit button and failure message are German
  it("labels the login form in German and reports failures in German", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockRejectedValue(
      new apiClient.ApiError("Not authenticated", 401),
    );
    vi.spyOn(apiClient, "postJson").mockRejectedValue(
      new apiClient.ApiError("Invalid credentials", 401),
    );

    renderWithProviders(<Login />);

    // Assert — labels
    expect(await screen.findByRole("textbox", { name: /benutzername/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/passwort/i)).toBeInTheDocument();
    const submit = screen.getByRole("button", { name: "Anmelden" });

    // Act — submit rejected credentials
    await userEvent.type(screen.getByRole("textbox", { name: /benutzername/i }), "alice");
    await userEvent.type(screen.getByLabelText(/passwort/i), "wrong");
    await userEvent.click(submit);

    // Assert — German failure message
    expect(await screen.findByText("Benutzername oder Passwort ist falsch.")).toBeInTheDocument();
  });
});
