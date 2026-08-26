import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useCurrentUser, useLogin } from "../hooks/useAuth";

export function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const { data: currentUser } = useCurrentUser();
  const login = useLogin();

  if (currentUser) {
    return <Navigate to="/" replace />;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    login.mutate({ username, password }, { onSuccess: () => navigate("/", { replace: true }) });
  }

  return (
    <div className="mx-auto mt-16 max-w-sm rounded bg-white p-6 shadow">
      <h1 className="mb-4 text-lg font-semibold text-gray-800">Picnic Ausgaben-Tracker</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Benutzername
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="rounded border border-gray-300 px-3 py-2"
            autoComplete="username"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-700">
          Passwort
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded border border-gray-300 px-3 py-2"
            autoComplete="current-password"
            required
          />
        </label>
        {login.isError && (
          <p className="text-sm text-red-600">Benutzername oder Passwort ist falsch.</p>
        )}
        <button
          type="submit"
          disabled={login.isPending}
          className="rounded bg-gray-800 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {login.isPending ? "Wird angemeldet…" : "Anmelden"}
        </button>
      </form>
    </div>
  );
}
