import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Button } from "./components/ui/Button";
import { useCurrentUser, useLogout } from "./hooks/useAuth";
import { Articles } from "./pages/Articles";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Receipts } from "./pages/Receipts";
import { Stats } from "./pages/Stats";

const NAV_LINKS = [
  { to: "/", label: "Übersicht" },
  { to: "/stats", label: "Statistiken" },
  { to: "/receipts", label: "Kassenbons" },
  { to: "/articles", label: "Artikel" },
];

export function LogoutButton() {
  const navigate = useNavigate();
  const logout = useLogout();

  return (
    <Button
      variant="ghost"
      onClick={() =>
        logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) })
      }
    >
      Abmelden
    </Button>
  );
}

export function App() {
  const { data: currentUser } = useCurrentUser();

  return (
    <div className="min-h-screen bg-surface-muted">
      <header className="sticky top-0 z-20 border-b border-surface-border bg-surface/95 backdrop-blur">
        <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
          <span className="hidden shrink-0 text-sm font-semibold text-gray-900 sm:block">
            Picnic
          </span>
          <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                    isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-gray-600 hover:bg-surface-muted hover:text-gray-900"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
          {currentUser && <LogoutButton />}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />
          <Route
            path="/articles"
            element={
              <ProtectedRoute>
                <Articles />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stats"
            element={
              <ProtectedRoute>
                <Stats />
              </ProtectedRoute>
            }
          />
          <Route
            path="/receipts"
            element={
              <ProtectedRoute>
                <Receipts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/receipts/:id"
            element={
              <ProtectedRoute>
                <Receipts />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
