"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";

const NAV = [
  { href: "/conversas", label: "Conversas" },
  { href: "/base-conhecimento", label: "Base de conhecimento" },
  { href: "/tools", label: "Tools" },
  { href: "/handoffs", label: "Handoffs" },
  { href: "/configuracoes", label: "Configurações" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const tenantName = (session as any)?.tenantName as string | undefined;

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-col bg-dark p-4 text-white">
        <div className="mb-8 px-2">
          <div className="text-xl font-bold">MayaSec</div>
          <div className="text-xs text-indigo">{tenantName || "Painel"}</div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  active ? "bg-navy text-white" : "text-slate-300 hover:bg-white/10"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="mt-4 rounded-lg px-3 py-2 text-left text-sm text-slate-400 hover:bg-white/10"
        >
          Sair
        </button>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
