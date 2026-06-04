"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "../lib/auth";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import { RefreshCw } from "lucide-react";

export default function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { loading, user } = useAuth();
  const isLoginPage = pathname === "/login";

  if (loading) {
    return (
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        width: "100vw",
        background: "var(--surface)",
        color: "var(--text)"
      }}>
        <RefreshCw className="skeleton" size={40} style={{ color: "var(--blue)", animation: "spin 0.6s linear infinite", borderRadius: "50%" }} />
        <span style={{ marginTop: "var(--space-4)", color: "var(--text-2)", fontWeight: 500 }}>
          Authenticating CheeseBall Admin Session...
        </span>
      </div>
    );
  }

  // If on login, just show the login component
  if (isLoginPage) {
    return <main style={{ minHeight: "100vh", width: "100%" }}>{children}</main>;
  }

  // If not logged in at all (redirecting), show empty to prevent flash
  if (!user) {
    return null;
  }

  return (
    <div className="layout-wrapper">
      <Sidebar />
      <div className="main-content">
        <Header />
        <main className="content-container">{children}</main>
      </div>
    </div>
  );
}
