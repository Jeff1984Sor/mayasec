"use client";
import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiSend, apiDownload, apiUpload } from "@/lib/api";
import { PageHeader, Card, Button, EmptyState, Modal, Badge } from "@/components/ui";

type Faq = { id: string; question: string; answer: string; tags: string[] | null; is_active: boolean };

export default function BaseConhecimentoPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Faq | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const faqs = useQuery({ queryKey: ["faq"], queryFn: () => apiGet<Faq[]>("/panel/knowledge-base") });

  const save = useMutation({
    mutationFn: () =>
      editing
        ? apiSend("PUT", `/panel/knowledge-base/${editing.id}`, { question, answer, is_active: true })
        : apiSend("POST", "/panel/knowledge-base", { question, answer, is_active: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["faq"] });
      setOpen(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiSend("DELETE", `/panel/knowledge-base/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["faq"] }),
  });

  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadMsg, setUploadMsg] = useState("");

  const upload = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("replace", "false");
      return apiUpload("/panel/knowledge-base/upload", fd);
    },
    onSuccess: (r: any) => {
      setUploadMsg(`${r.inseridas} pergunta(s) importada(s)!`);
      qc.invalidateQueries({ queryKey: ["faq"] });
      setTimeout(() => setUploadMsg(""), 4000);
    },
    onError: () => setUploadMsg("Falha ao importar. Confira o arquivo (2 colunas)."),
  });

  function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) upload.mutate(f);
    e.target.value = "";
  }

  function openNew() {
    setEditing(null);
    setQuestion("");
    setAnswer("");
    setOpen(true);
  }
  function openEdit(f: Faq) {
    setEditing(f);
    setQuestion(f.question);
    setAnswer(f.answer);
    setOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Base de conhecimento"
        subtitle="Perguntas e respostas que a secretária usa"
        action={
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => apiDownload("/panel/knowledge-base/template", "modelo-faq.xlsx")}>
              ↓ Baixar planilha
            </Button>
            <Button variant="ghost" onClick={() => fileRef.current?.click()} disabled={upload.isPending}>
              {upload.isPending ? "Importando..." : "↑ Subir planilha"}
            </Button>
            <Button onClick={openNew}>+ Nova pergunta</Button>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.csv"
              className="hidden"
              onChange={onPickFile}
            />
          </div>
        }
      />

      {uploadMsg && (
        <div className="mb-4 rounded-lg bg-teal/10 px-3 py-2 text-sm text-teal">{uploadMsg}</div>
      )}

      {faqs.data?.length === 0 && <EmptyState message="Nenhuma FAQ cadastrada." />}

      <div className="grid gap-3">
        {faqs.data?.map((f) => (
          <Card key={f.id} className="flex items-start justify-between">
            <div>
              <div className="font-semibold">{f.question}</div>
              <div className="mt-1 text-sm text-slate-600">{f.answer}</div>
              {!f.is_active && <div className="mt-2"><Badge color="slate">inativa</Badge></div>}
            </div>
            <div className="flex shrink-0 gap-2">
              <Button variant="ghost" onClick={() => openEdit(f)}>Editar</Button>
              <Button variant="danger" onClick={() => remove.mutate(f.id)}>Excluir</Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Editar pergunta" : "Nova pergunta"}>
        <label className="mb-1 block text-sm font-medium">Pergunta</label>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" />
        <label className="mb-1 block text-sm font-medium">Resposta</label>
        <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={4} className="mb-4 w-full rounded-lg border border-slate-200 px-3 py-2 outline-none focus:border-indigo" />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>Salvar</Button>
        </div>
      </Modal>
    </div>
  );
}
