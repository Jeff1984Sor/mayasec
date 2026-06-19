"use client";
import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend, apiUpload } from "@/lib/api";
import { PageHeader, Card, EmptyState, Badge, Button } from "@/components/ui";

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

  const qc = useQueryClient();
  const [draft, setDraft] = useState("");

  const mensagens = useQuery({
    queryKey: ["messages", selected],
    queryFn: () => apiGet<any[]>(`/panel/conversations/${selected}/messages`),
    enabled: !!selected,
  });

  const selectedConv = conversas.data?.find((c) => c.id === selected);

  const reply = useMutation({
    mutationFn: (text: string) => apiSend("POST", `/panel/conversations/${selected}/reply`, { text }),
    onSuccess: () => {
      setDraft("");
      qc.invalidateQueries({ queryKey: ["messages", selected] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const reactivate = useMutation({
    mutationFn: () => apiSend("PATCH", `/panel/conversations/${selected}/state`, { state: "idle" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });

  const mediaRef = useRef<HTMLInputElement>(null);
  const sendMedia = useMutation({
    mutationFn: (f: File) => {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("caption", draft.trim());
      return apiUpload(`/panel/conversations/${selected}/reply-media`, fd);
    },
    onSuccess: () => {
      setDraft("");
      qc.invalidateQueries({ queryKey: ["messages", selected] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  function onPickMedia(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) sendMedia.mutate(f);
    e.target.value = "";
  }

  const rename = useMutation({
    mutationFn: ({ contactId, name }: { contactId: string; name: string }) =>
      apiSend("PATCH", `/panel/contacts/${contactId}`, { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });

  function onRename() {
    if (!selectedConv) return;
    const atual = selectedConv.contact.name || "";
    const novo = window.prompt("Nome do contato:", atual);
    if (novo !== null) rename.mutate({ contactId: selectedConv.contact.id, name: novo });
  }

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

        <Card className="flex max-h-[70vh] flex-col">
          {!selected && <EmptyState message="Selecione uma conversa para ver o histórico." />}
          {selected && (
            <>
              <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <div className="font-semibold">{selectedConv?.contact.name || selectedConv?.contact.phone_pn}</div>
                  <div className="text-xs text-slate-400">{selectedConv?.contact.phone_pn}</div>
                </div>
                <button onClick={onRename} title="Editar nome do contato" className="rounded-lg px-2 py-1 text-slate-500 hover:bg-slate-100">
                  ✏️ Editar nome
                </button>
              </div>

              {selectedConv?.state === "handoff_humano" && (
                <div className="mb-3 flex items-center justify-between rounded-lg bg-red/10 px-3 py-2 text-sm text-red">
                  <span>Secretária pausada (atendimento humano)</span>
                  <button onClick={() => reactivate.mutate()} className="font-semibold underline">
                    Reativar secretária
                  </button>
                </div>
              )}

              <div className="flex flex-1 flex-col gap-2 overflow-auto">
                {mensagens.isLoading && <div className="text-slate-400">Carregando mensagens...</div>}
                {mensagens.data?.map((m) => (
                  <div
                    key={m.id}
                    className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                      m.direction === "inbound" ? "self-start bg-slate-100" : "self-end bg-navy text-white"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.body}</div>
                    <div className={`mt-1 text-[10px] ${m.direction === "inbound" ? "text-slate-400" : "text-indigo"}`}>
                      {new Date(m.created_at).toLocaleString("pt-BR")}
                    </div>
                  </div>
                ))}
              </div>

              <form
                className="mt-3 flex gap-2 border-t border-slate-100 pt-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (draft.trim()) reply.mutate(draft.trim());
                }}
              >
                <button
                  type="button"
                  onClick={() => mediaRef.current?.click()}
                  disabled={sendMedia.isPending}
                  title="Anexar imagem, áudio ou PDF"
                  className="rounded-lg bg-slate-100 px-3 text-lg text-slate-600 hover:bg-slate-200"
                >
                  {sendMedia.isPending ? "…" : "📎"}
                </button>
                <input
                  ref={mediaRef}
                  type="file"
                  accept="image/*,audio/*,application/pdf"
                  className="hidden"
                  onChange={onPickMedia}
                />
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Responder como humano... (vira legenda ao anexar)"
                  className="flex-1 rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo"
                />
                <Button type="submit" disabled={reply.isPending || !draft.trim()}>
                  {reply.isPending ? "Enviando..." : "Enviar"}
                </Button>
              </form>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
