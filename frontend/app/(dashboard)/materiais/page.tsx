"use client";
import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend, apiUpload } from "@/lib/api";
import { PageHeader, Card, Button, EmptyState, Modal } from "@/components/ui";

type Material = { id: string; nome: string; descricao: string | null; arquivo: string | null };

export default function MateriaisPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const materiais = useQuery({ queryKey: ["materials"], queryFn: () => apiGet<Material[]>("/panel/materials") });

  const create = useMutation({
    mutationFn: () => {
      const f = fileRef.current?.files?.[0];
      if (!f) throw new Error("sem arquivo");
      const fd = new FormData();
      fd.append("nome", nome);
      fd.append("descricao", descricao);
      fd.append("file", f);
      return apiUpload("/panel/materials", fd);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials"] });
      setOpen(false);
      setNome("");
      setDescricao("");
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiSend("DELETE", `/panel/materials/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["materials"] }),
  });

  return (
    <div>
      <PageHeader
        title="Materiais"
        subtitle="PDFs que a secretária envia automaticamente quando o cliente pede"
        action={<Button onClick={() => setOpen(true)}>+ Novo material</Button>}
      />

      {materiais.data?.length === 0 && <EmptyState message="Nenhum material cadastrado." />}

      <div className="grid gap-3">
        {materiais.data?.map((m) => (
          <Card key={m.id} className="flex items-center justify-between">
            <div>
              <div className="font-semibold">{m.nome}</div>
              {m.descricao && <div className="text-sm text-slate-600">{m.descricao}</div>}
              <div className="mt-1 text-xs text-slate-400">📄 {m.arquivo}</div>
            </div>
            <Button variant="danger" onClick={() => remove.mutate(m.id)}>Excluir</Button>
          </Card>
        ))}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Novo material">
        <label className="mb-1 block text-sm font-medium">Nome (como o cliente pede)</label>
        <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Tabela de Produtos" className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" />
        <label className="mb-1 block text-sm font-medium">Descrição (ajuda a IA a saber quando enviar)</label>
        <input value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Ex.: lista de produtos e preços" className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" />
        <label className="mb-1 block text-sm font-medium">Arquivo (PDF)</label>
        <input ref={fileRef} type="file" accept="application/pdf,image/*" className="mb-4 w-full text-sm" />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button onClick={() => create.mutate()} disabled={create.isPending || !nome.trim()}>
            {create.isPending ? "Enviando..." : "Salvar"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
