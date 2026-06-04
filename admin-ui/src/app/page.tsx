"use client";

import React, { useState, useEffect } from "react";
import Head from "next/head";
import { api } from "../lib/api";
import StatsCard from "../components/StatsCard";
import AreaChart from "../components/Charts";
import DataTable, { Column } from "../components/DataTable";
import StatusBadge from "../components/StatusBadge";
import Link from "next/link";
import {
  Users,
  ArrowUpDown,
  FileCheck,
  Download,
  Activity,
  DollarSign,
  TrendingUp,
  RefreshCw,
  Clock,
  ArrowUpRight
} from "lucide-react";

interface DashboardStats {
  total_users: number;
  verified_users: number;
  pending_kyc: number;
  total_transactions: number;
  pending_transactions: number;
  pending_withdrawals: number;
  total_volume_ngn: number;
  total_volume_24h_ngn: number;
}

interface RecentTransaction {
  id: string;
  user_email: string;
  transaction_type: string;
  asset: string;
  status: string;
  naira_amount: number;
  crypto_amount: number;
  final_rate: number;
  created_at: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTxns, setRecentTxns] = useState<RecentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const statsRes = await api.get<DashboardStats>("/admin/stats");
      setStats(statsRes);
      
      const txnsRes = await api.get<{ transactions: RecentTransaction[] }>("/admin/transactions", {
        page_size: 6,
      });
      setRecentTxns(txnsRes.transactions || []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Mock chart data representing recent daily volumes (could be derived or static for visualization)
  const chartData = [
    { label: "Mon", value: stats ? stats.total_volume_24h_ngn * 0.4 : 120000 },
    { label: "Tue", value: stats ? stats.total_volume_24h_ngn * 0.7 : 180000 },
    { label: "Wed", value: stats ? stats.total_volume_24h_ngn * 0.5 : 150000 },
    { label: "Thu", value: stats ? stats.total_volume_24h_ngn * 0.9 : 280000 },
    { label: "Fri", value: stats ? stats.total_volume_24h_ngn * 1.2 : 320000 },
    { label: "Sat", value: stats ? stats.total_volume_24h_ngn * 0.8 : 220000 },
    { label: "Sun", value: stats ? stats.total_volume_24h_ngn : 450000 },
  ];

  const columns: Column<RecentTransaction>[] = [
    {
      header: "User Email",
      accessor: "user_email",
      cell: (row) => <span style={{ fontWeight: 600 }}>{row.user_email}</span>,
    },
    {
      header: "Type",
      accessor: "transaction_type",
      cell: (row) => (
        <span style={{
          textTransform: "uppercase",
          fontWeight: 700,
          fontSize: "11px",
          color: row.transaction_type.toLowerCase() === "buy" ? "var(--green-text)" : "var(--blue)"
        }}>
          {row.transaction_type}
        </span>
      ),
    },
    {
      header: "Asset",
      accessor: "asset",
      cell: (row) => <span style={{ fontWeight: 600 }}>{row.asset}</span>,
    },
    {
      header: "Amount (NGN)",
      accessor: "naira_amount",
      cell: (row) => <span>₦{Number(row.naira_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>,
    },
    {
      header: "Crypto Amount",
      accessor: "crypto_amount",
      cell: (row) => <span>{row.crypto_amount} {row.asset}</span>,
    },
    {
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Actions",
      cell: (row) => (
        <Link href={`/transactions/${row.id}`} className="btn btn-secondary btn-sm">
          Details
        </Link>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard Overview</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Platform summary and operational review queue.</p>
        </div>
        
        <button
          onClick={fetchDashboardData}
          className="btn btn-secondary"
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? "skeleton" : ""} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Refresh Stats
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid-cols-4" style={{ marginBottom: "var(--space-6)" }}>
        <StatsCard
          label="Total Users"
          value={loading ? "..." : stats?.total_users || 0}
          change={stats ? { value: `${stats.verified_users} Verified`, isPositive: true } : undefined}
          icon={Users}
        />
        <StatsCard
          label="Total Volume NGN"
          value={loading ? "..." : `₦${Number(stats?.total_volume_ngn || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          change={stats ? { value: "Cumulative platform total", isPositive: true } : undefined}
          icon={DollarSign}
        />
        <StatsCard
          label="24h Volume NGN"
          value={loading ? "..." : `₦${Number(stats?.total_volume_24h_ngn || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          change={stats ? { value: "Daily platform volume", isPositive: true } : undefined}
          icon={Activity}
        />
        <StatsCard
          label="Review Queue"
          value={loading ? "..." : (stats?.pending_kyc || 0) + (stats?.pending_withdrawals || 0) + (stats?.pending_transactions || 0)}
          change={stats ? { value: `${stats.pending_kyc} KYC • ${stats.pending_withdrawals} Wd`, isPositive: false } : undefined}
          icon={Clock}
        />
      </div>

      <div className="grid-cols-3" style={{ marginBottom: "var(--space-6)" }}>
        {/* Chart Column */}
        <div className="card" style={{ gridColumn: "span 2", marginBottom: 0 }}>
          <h3 className="section-title">24h Transaction Volume Trend</h3>
          <div style={{ height: "250px", marginTop: "var(--space-4)" }}>
            <AreaChart data={chartData} height={240} prefix="₦" />
          </div>
        </div>

        {/* Quick Review Actions column */}
        <div className="card" style={{ marginBottom: 0 }}>
          <h3 className="section-title">Quick Approvals</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
              <div>
                <div style={{ fontWeight: 600 }}>Pending KYC Submissions</div>
                <div style={{ fontSize: "12px", color: "var(--text-2)" }}>{loading ? "..." : stats?.pending_kyc || 0} user documents waiting</div>
              </div>
              <Link href="/kyc" className="btn btn-primary btn-sm" style={{ display: "flex", gap: "4px" }}>
                Review <ArrowUpRight size={14} />
              </Link>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
              <div>
                <div style={{ fontWeight: 600 }}>Pending Withdrawals</div>
                <div style={{ fontSize: "12px", color: "var(--text-2)" }}>{loading ? "..." : stats?.pending_withdrawals || 0} payouts to process</div>
              </div>
              <Link href="/withdrawals" className="btn btn-primary btn-sm" style={{ display: "flex", gap: "4px" }}>
                Process <ArrowUpRight size={14} />
              </Link>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
              <div>
                <div style={{ fontWeight: 600 }}>Pending Transactions</div>
                <div style={{ fontSize: "12px", color: "var(--text-2)" }}>{loading ? "..." : stats?.pending_transactions || 0} buy/sell reviews</div>
              </div>
              <Link href="/transactions" className="btn btn-primary btn-sm" style={{ display: "flex", gap: "4px" }}>
                Handle <ArrowUpRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Transactions Table */}
      <div className="card">
        <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-4)" }}>
          <h3 className="section-title" style={{ marginBottom: 0 }}>Recent Platform Activity</h3>
          <Link href="/transactions" style={{ fontSize: "13px", fontWeight: 600, display: "flex", alignItems: "center", gap: "2px" }}>
            View all transactions <ArrowUpRight size={14} />
          </Link>
        </div>
        <DataTable
          columns={columns}
          data={recentTxns}
          loading={loading}
          emptyMessage="No recent transactions found on the platform."
        />
      </div>
    </div>
  );
}
