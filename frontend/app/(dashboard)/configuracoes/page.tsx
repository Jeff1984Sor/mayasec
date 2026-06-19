"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend } from "@/lib/api";
import { PageHeader, Card, Button, Badge } from "@/components/ui";

export default function ConfiguracoesPage() {
  const qc = useQueryClient();
  const cfg = useQuery({ queryKey: ["config"], queryFn: () => apiGet<any>("/panel/config") });

  const [voiceTone, setVoiceTone] = useState("");
  const [maxMsgs, setMaxMsgs] = useState<string>("");
  const [windowS, setWindowS] = useState<string>("");
  const [baseUrl, setBaseUrl] = useState("");
  const [credential, setCredential] = useState("");
  const [mock, setMock] = useState(true);

  useEffect(() => {
    if (cfg.data) {
      setVoiceTone(cfg.data.voice_tone || "");
      setMaxMsgs(cfg.data.antiflood_max_msgs ?? "");
      setWindowS(cfg.data.antiflood_window_seconds ?? "");
      setBaseUrl(cfg.data.client_api_base_url || "");
      setMock(cfg.data.client_api_mock);
    }
  }, [cfg.data]);

  const save = useMutation({
    mutationFn: () =>
      apiSend("PUT", "/panel/config", {
        voice_tone: voiceTone,
        antiflood_max_msgs: maxMsgs === "" ? null : Number(maxMsgs),
        antiflood_window_seconds: windowS === "" ? null : Number(windowS),
        client_api_base_url: baseUrl,
        client_api_credential: credential || undefined,
        client_api_mock: mock,
      }),
    onSuccess: () => {
      setCredential("");
      qc.invalidateQueries({ queryKey: ["config"] });
    },
  });

  return (
    <div className="max-w-2xl">
      <PageHeader title="Configurações" subtitle={cfg.data?.name} />

      <Card className="mb-4">
        <h3 className="mb-3 font-semibold text-navy">Secretária</h3>
        <label className="mb-1 block text-sm font-medium">Tom de voz</label>
        <textarea value={voiceTone} onChange={(e) => setVoiceTone(e.target.value)} rows={3} className="w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" />
      </Card>

      <Card className="mb-4">
        <h3 className="mb-3 font-semibold text-navy">Anti-flood</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Máx. mensagens</label>
            <input value={maxMsgs} onChange={(e) => setMaxMsgs(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" placeholder="default global" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Janela (segundos)</label>
            <input value={windowS} onChange={(e) => setWindowS(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" placeholder="default global" />
          </div>
        </div>
      </Card>

      <Card className="mb-6">
        <div className="mb-3 flex items-center gap-2">
          <h3 className="font-semibold text-navy">Conexão com seu sistema</h3>
          {mock ? <Badge color="amber">mock</Badge> : <Badge color="teal">real</Badge>}
        </div>
        <label className="mb-1 block text-sm font-medium">URL base da API</label>
        <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" placeholder="https://seusistema/api" />
        <label className="mb-1 block text-sm font-medium">Credencial (deixe em branco para manter)</label>
        <input value={credential} onChange={(e) => setCredential(e.target.value)} type="password" className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" placeholder={cfg.data?.has_client_api_credential ? "•••••• (configurada)" : ""} />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={mock} onChange={(e) => setMock(e.target.checked)} />
          Modo mock (responde dados fake sem chamar a API real)
        </label>
      </Card>

      <Button onClick={() => save.mutate()} disabled={save.isPending}>
        {save.isPending ? "Salvando..." : "Salvar configurações"}
      </Button>
    </div>
  );
}
