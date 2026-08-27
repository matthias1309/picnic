import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useCurrentUser, useLogin } from "../hooks/useAuth";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

const FIELD_CLASSES =
  "rounded-lg border border-surface-border bg-surface px-3 py-2 text-gray-900 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500";

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
    <div className="mx-auto mt-16 max-w-sm">
      <Card>
        <h1 className="mb-1 text-lg font-semibold text-gray-900">Picnic Ausgaben-Tracker</h1>
        <p className="mb-5 text-sm text-gray-500">Melde dich an, um deine Ausgaben zu sehen.</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
            Benutzername
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className={FIELD_CLASSES}
              autoComplete="username"
              required
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium text-gray-700">
            Passwort
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={FIELD_CLASSES}
              autoComplete="current-password"
              required
            />
          </label>
          {login.isError && (
            <p className="text-sm text-negative-700">Benutzername oder Passwort ist falsch.</p>
          )}
          <Button type="submit" disabled={login.isPending} className="mt-1 w-full py-2">
            {login.isPending ? "Wird angemeldet…" : "Anmelden"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
