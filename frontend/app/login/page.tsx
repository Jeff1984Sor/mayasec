"use client";
import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const res = await signIn("credentials", { email, password, redirect: false });
    setLoading(false);
    if (res?.error) {
      setError("Email ou senha inválidos.");
    } else {
      router.push("/conversas");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-dark">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl"
      >
        <h1 className="mb-1 text-2xl font-bold text-navy">MayaSec</h1>
        <p className="mb-6 text-sm text-slate-500">Painel da secretária virtual</p>

        {error && (
          <div className="mb-4 rounded-lg bg-red/10 px-3 py-2 text-sm text-red">{error}</div>
        )}

        <label className="mb-1 block text-sm font-medium">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo"
          required
        />

        <label className="mb-1 block text-sm font-medium">Senha</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-6 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo"
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-navy py-2.5 font-semibold text-white hover:bg-navy/90 disabled:opacity-60"
        >
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
