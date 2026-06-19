"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { PageHeader, Card, EmptyState, Badge } from "@/components/ui";

const STATE_COLOR: Record<string, any> = {
  idle: "slate",
  aguardando_confirmacao: "amber",
  em_atendimento: "teal",
  handoff_humano: "red",
};

export default function ConversasPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const conversas = useQuery({
    queryKey: ["conversations"],
    queryFn: () => apiGet<any[]>("/panel/conversations"),
  });

  const mensagens = useQuery({
    queryKey: ["messages", selected],
    queryFn: () => apiGet<any[]>(`/panel/conversations/${selected}/messages`),
    enabled: !!selected,
  });

  return (
    <div>
      <PageHeader title="Conversas" subtitle="Histórico de atendimentos por contato" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
        <Card className="max-h-[70vh] overflow-auto p-0">
          {conversas.isLoading && <div className="p-5 text-slate-400">Carregando...</div>}
          {conversas.data?.length === 0 && <div className="p-5 text-slate-400">Nenhuma conversa ainda.</div>}
          <ul className="divide-y divide-slate-100">
            {conversas.data?.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => setSelected(c.id)}
                  className={`flex w-full items-center justify-between px-5 py-3 text-left hover:bg-slate-50 ${selected === c.id ? "bg-slate-50" : ""}`}
                >
                  <div>
                    <div className="font-medium">{c.contact.name || c.contact.phone_pn}</div>
                    <div className="text-xs text-slate-400">{c.contact.phone_pn}</div>
                  </div>
                  <Badge color={STATE_COLOR[c.state] || "slate"}>{c.state}</Badge>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="max-h-[70vh] overflow-auto">
          {!selected && <EmptyState message="Selecione uma conversa para ver o histórico." />}
          {selected && mensagens.isLoading && <div className="text-slate-400">Carregando mensagens...</div>}
          {selected && mensagens.data && (
            <div className="flex flex-col gap-2">
              {mensagens.data.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                    m.direction === "inbound"
                      ? "self-start bg-slate-100"
                      : "self-end bg-navy text-white"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.body}</div>
                  <div className={`mt-1 text-[10px] ${m.direction === "inbound" ? "text-slate-400" : "text-indigo"}`}>
                    {new Date(m.created_at).toLocaleString("pt-BR")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
