"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../lib/auth";
import {
  LayoutDashboard,
  Users,
  ArrowUpDown,
  FileCheck,
  Download,
  Wallet,
  Percent,
  Coins,
  Cpu,
  LogOut,
  ChevronLeft,
  ChevronRight,
  TrendingUp
} from "lucide-react";
import { useState } from "react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Users", href: "/users", icon: Users },
    { name: "Transactions", href: "/transactions", icon: ArrowUpDown },
    { name: "KYC Review", href: "/kyc", icon: FileCheck },
    { name: "Withdrawals", href: "/withdrawals", icon: Download },
    { name: "Wallets & Ledger", href: "/wallets", icon: Wallet },
    { name: "Markup Rates", href: "/rates", icon: Percent },
    { name: "Reserves", href: "/reserves", icon: Coins },
    { name: "Quidax Sync", href: "/quidax", icon: Cpu },
  ];

  const handleToggle = () => {
    setCollapsed(!collapsed);
    if (typeof window !== "undefined") {
      const root = document.documentElement;
      root.style.setProperty("--sidebar-width", collapsed ? "260px" : "80px");
      root.style.setProperty("--sidebar-collapsed", collapsed ? "80px" : "80px");
    }
  };

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`} style={{ width: collapsed ? "80px" : "260px" }}>
      <div className="sidebar-logo" style={{ padding: collapsed ? "0 0 var(--space-4) 0" : "0 var(--space-6) var(--space-6)", justifyContent: collapsed ? "center" : "space-between" }}>
        {!collapsed && (
          <span style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 800 }}>
            <TrendingUp size={24} style={{ color: "var(--blue)" }} />
            CheeseBall <span style={{ fontSize: "11px", fontWeight: 600, background: "var(--blue-light)", color: "var(--blue)", padding: "2px 6px", borderRadius: "var(--radius-sm)" }}>Admin</span>
          </span>
        )}
        {collapsed && <TrendingUp size={24} style={{ color: "var(--blue)" }} />}
      </div>

      <nav className="sidebar-menu" style={{ padding: "0 var(--space-2)" }}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-item ${isActive ? "active" : ""}`}
              style={{
                borderRadius: "var(--radius-md)",
                margin: "2px 0",
                justifyContent: collapsed ? "center" : "flex-start",
                padding: collapsed ? "12px 0" : "12px var(--space-4)",
                gap: collapsed ? "0" : "var(--space-3)"
              }}
              title={collapsed ? item.name : undefined}
            >
              <Icon size={20} />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button
          onClick={logout}
          className="sidebar-item"
          style={{
            width: "100%",
            background: "none",
            border: "none",
            borderRadius: "var(--radius-md)",
            cursor: "pointer",
            justifyContent: collapsed ? "center" : "flex-start",
            padding: collapsed ? "12px 0" : "12px var(--space-4)",
            color: "var(--red)",
            gap: collapsed ? "0" : "var(--space-3)"
          }}
          title={collapsed ? "Logout" : undefined}
        >
          <LogOut size={20} />
          {!collapsed && <span>Logout</span>}
        </button>

        <button
          onClick={handleToggle}
          style={{
            width: "100%",
            background: "none",
            border: "none",
            borderTop: "1px solid var(--border)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "var(--space-3) 0 0",
            color: "var(--text-3)",
            marginTop: "var(--space-2)"
          }}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
    </aside>
  );
}
