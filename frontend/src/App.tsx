import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useCurrentUser, useLogout } from "./hooks/useAuth";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Receipts } from "./pages/Receipts";
import { Stats } from "./pages/Stats";

const NAV_LINKS = [
  { to: "/", label: "Übersicht" },
  { to: "/stats", label: "Statistiken" },
  { to: "/receipts", label: "Kassenbons" },
];

export function LogoutButton() {
  const navigate = useNavigate();
  const logout = useLogout();

  return (
    <button
      type="button"
      onClick={() =>
        logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) })
      }
      className="rounded px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-100"
    >
      Abmelden
    </button>
  );
}

export function App() {
  const { data: currentUser } = useCurrentUser();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex gap-4">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `rounded px-3 py-1 text-sm font-medium ${
                    isActive ? "bg-gray-800 text-white" : "text-gray-700 hover:bg-gray-100"
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
      <main className="mx-auto max-w-5xl px-4 py-6">
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
