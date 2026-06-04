"use client";

import { useAuth } from "../lib/auth";
import { User as UserIcon, RefreshCw, Server } from "lucide-react";
import { getApiUrl } from "../lib/api";

export default function Header() {
  const { user } = useAuth();
  const apiUrl = getApiUrl();

  return (
    <header className="navbar">
      <div className="flex items-center gap-3">
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", background: "var(--surface)", padding: "6px 12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
          <Server size={14} style={{ color: "var(--text-2)" }} />
          <span style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 500 }}>
            API: <code style={{ color: "var(--blue)", fontWeight: 600 }}>{apiUrl}</code>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3" style={{ borderLeft: "1px solid var(--border)", paddingLeft: "var(--space-4)" }}>
            <div className="flex flex-col text-right">
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                {user.first_name} {user.last_name}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-2)" }}>
                {user.email}
              </span>
            </div>
            
            <div style={{
              width: "36px",
              height: "36px",
              borderRadius: "var(--radius-full)",
              background: "var(--blue-light)",
              color: "var(--blue)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: "14px",
              border: "1px solid var(--border)"
            }}>
              {user.first_name ? user.first_name[0].toUpperCase() : <UserIcon size={16} />}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
