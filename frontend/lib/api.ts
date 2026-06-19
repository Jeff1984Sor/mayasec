"use client";
import { getSession } from "next-auth/react";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8011";

async function authHeader(): Promise<Record<string, string>> {
  const session = await getSession();
  const token = (session as any)?.backendToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet<T = any>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { ...(await authHeader()) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { headers: { ...(await authHeader()) } });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function apiUpload<T = any>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { ...(await authHeader()) },
    body: formData,
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json();
}

export async function apiSend<T = any>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}`);
  return res.status === 204 ? (undefined as T) : res.json();
}
