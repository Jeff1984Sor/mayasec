"use client";
import React from "react";

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between">
      <div>
        <h1 className="text-2xl font-bold text-navy">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-2xl bg-white p-5 shadow-sm ${className}`}>{children}</div>;
}

export function Button({ children, onClick, variant = "primary", type = "button", disabled }: {
  children: React.ReactNode; onClick?: () => void; variant?: "primary" | "ghost" | "danger"; type?: "button" | "submit"; disabled?: boolean;
}) {
  const styles = {
    primary: "bg-navy text-white hover:bg-navy/90",
    ghost: "bg-slate-100 text-slate-700 hover:bg-slate-200",
    danger: "bg-red text-white hover:bg-red/90",
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-60 ${styles}`}>
      {children}
    </button>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center text-slate-400">{message}</div>;
}

export function Badge({ children, color = "indigo" }: { children: React.ReactNode; color?: "indigo" | "teal" | "amber" | "red" | "slate" }) {
  const map: Record<string, string> = {
    indigo: "bg-indigo/15 text-navy",
    teal: "bg-teal/15 text-teal",
    amber: "bg-amber/20 text-amber",
    red: "bg-red/15 text-red",
    slate: "bg-slate-100 text-slate-500",
  };
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${map[color]}`}>{children}</span>;
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-4 text-lg font-bold text-navy">{title}</h2>
        {children}
      </div>
    </div>
  );
}
