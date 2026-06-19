"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend } from "@/lib/api";
import { PageHeader, Card, Badge } from "@/components/ui";

type Tool = { name: string; description: string; is_enabled: boolean };

export default function ToolsPage() {
  const qc = useQueryClient();
  const tools = useQuery({ queryKey: ["tools"], queryFn: () => apiGet<Tool[]>("/panel/tools") });

  const toggle = useMutation({
    mutationFn: (t: Tool) => apiSend("PUT", `/panel/tools/${t.name}`, { is_enabled: !t.is_enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tools"] }),
  });

  return (
    <div>
      <PageHeader title="Tools" subtitle="Ações que a secretária pode executar no seu sistema" />
      <div className="grid gap-3">
        {tools.data?.map((t) => (
          <Card key={t.name} className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold">{t.name}</span>
                {t.is_enabled ? <Badge color="teal">ativa</Badge> : <Badge color="slate">inativa</Badge>}
              </div>
              <div className="mt-1 text-sm text-slate-600">{t.description}</div>
            </div>
            <button
              onClick={() => toggle.mutate(t)}
              className={`relative h-6 w-11 rounded-full transition ${t.is_enabled ? "bg-teal" : "bg-slate-300"}`}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${t.is_enabled ? "left-[22px]" : "left-0.5"}`} />
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}
