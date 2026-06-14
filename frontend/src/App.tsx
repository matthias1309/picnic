import { NavLink, Route, Routes } from "react-router-dom";
import { Home } from "./pages/Home";
import { Receipts } from "./pages/Receipts";
import { Stats } from "./pages/Stats";

const NAV_LINKS = [
  { to: "/", label: "Home" },
  { to: "/stats", label: "Stats" },
  { to: "/receipts", label: "Receipts" },
];

export function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <nav className="mx-auto flex max-w-5xl gap-4 px-4 py-3">
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
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/receipts" element={<Receipts />} />
          <Route path="/receipts/:id" element={<Receipts />} />
        </Routes>
      </main>
    </div>
  );
}
