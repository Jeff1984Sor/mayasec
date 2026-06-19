"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend } from "@/lib/api";
import { PageHeader, Card, EmptyState, Badge, Button } from "@/components/ui";

type Handoff = {
  id: string;
  contact: { phone_pn: string; name: string | null };
  reason: string | null;
  status: string;
  created_at: string;
};

const STATUS_COLOR: Record<string, any> = { open: "amber", in_progress: "indigo", resolved: "teal" };
const NEXT: Record<string, string> = { open: "in_progress", in_progress: "resolved" };

export default function HandoffsPage() {
  const qc = useQueryClient();
  const handoffs = useQuery({ queryKey: ["handoffs"], queryFn: () => apiGet<Handoff[]>("/panel/handoffs") });

  const advance = useMutation({
    mutationFn: (h: Handoff) => apiSend("PATCH", `/panel/handoffs/${h.id}`, { status: NEXT[h.status] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["handoffs"] }),
  });

  return (
    <div>
      <PageHeader title="Handoffs" subtitle="Conversas que a secretária passou para um humano" />
      {handoffs.data?.length === 0 && <EmptyState message="Nenhum handoff na fila." />}
      <div className="grid gap-3">
        {handoffs.data?.map((h) => (
          <Card key={h.id} className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{h.contact.name || h.contact.phone_pn}</span>
                <Badge color={STATUS_COLOR[h.status]}>{h.status}</Badge>
              </div>
              <div className="mt-1 text-sm text-slate-600">{h.reason || "—"}</div>
              <div className="mt-1 text-xs text-slate-400">{new Date(h.created_at).toLocaleString("pt-BR")}</div>
            </div>
            {NEXT[h.status] && (
              <Button variant="ghost" onClick={() => advance.mutate(h)}>
                {h.status === "open" ? "Assumir" : "Resolver"}
              </Button>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
