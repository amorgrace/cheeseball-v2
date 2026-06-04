"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import StatusBadge from "../../components/StatusBadge";
import { RefreshCw, ArrowDownLeft, ArrowUpRight, Cpu, Activity } from "lucide-react";

interface QuidaxDepositItem {
  id: string;
  user_email: string;
  currency: string;
  amount: number;
  status: string;
  txid: string;
  created_at: string;
}

interface QuidaxWithdrawalItem {
  id: string;
  user_email: string;
  currency: string;
  amount: number;
  status: string;
  reference: string;
  created_at: string;
}

interface QuidaxWebhookItem {
  id: string;
  event_type: string;
  provider_event_id: string;
  processed_at: string | null;
  created_at: string;
}

interface QuidaxResponse {
  deposits: QuidaxDepositItem[];
  deposits_meta: { total: number; page: number; page_size: number; total_pages: number };
  withdrawals: QuidaxWithdrawalItem[];
  withdrawals_meta: { total: number; page: number; page_size: number; total_pages: number };
  webhooks: QuidaxWebhookItem[];
}

export default function QuidaxPage() {
  const [activeTab, setActiveTab] = useState<"deposits" | "withdrawals" | "webhooks">("deposits");
  const [data, setData] = useState<QuidaxResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const fetchQuidaxData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<QuidaxResponse>("/admin/quidax", {
        page,
        page_size: 20,
      });
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load Quidax sync monitor logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuidaxData();
  }, [page, activeTab]);

  const depositColumns: Column<QuidaxDepositItem>[] = [
    {
      header: "User Email",
      accessor: "user_email",
      cell: (row) => <span style={{ fontWeight: 600 }}>{row.user_email}</span>,
    },
    {
      header: "Currency",
      accessor: "currency",
      cell: (row) => <span style={{ fontWeight: 700 }}>{row.currency}</span>,
    },
    {
      header: "Amount",
      accessor: "amount",
      cell: (row) => <span>{Number(row.amount).toLocaleString()}</span>,
    },
    {
      header: "TxID / Hash",
      accessor: "txid",
      cell: (row) => <span style={{ fontFamily: "monospace", fontSize: "11px", wordBreak: "break-all" }}>{row.txid}</span>,
    },
    {
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Received At",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  const withdrawalColumns: Column<QuidaxWithdrawalItem>[] = [
    {
      header: "User Email",
      accessor: "user_email",
      cell: (row) => <span style={{ fontWeight: 600 }}>{row.user_email}</span>,
    },
    {
      header: "Currency",
      accessor: "currency",
      cell: (row) => <span style={{ fontWeight: 700 }}>{row.currency}</span>,
    },
    {
      header: "Amount",
      accessor: "amount",
      cell: (row) => <span>{Number(row.amount).toLocaleString()}</span>,
    },
    {
      header: "Sync Reference",
      accessor: "reference",
      cell: (row) => <span style={{ fontFamily: "monospace", fontSize: "11px" }}>{row.reference}</span>,
    },
    {
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Disbursed At",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  const webhookColumns: Column<QuidaxWebhookItem>[] = [
    {
      header: "Event ID",
      accessor: "provider_event_id",
      cell: (row) => <span style={{ fontFamily: "monospace", fontSize: "11px" }}>{row.provider_event_id}</span>,
    },
    {
      header: "Event Type",
      accessor: "event_type",
      cell: (row) => <span style={{ fontWeight: 600, fontSize: "12px", textTransform: "uppercase" }}>{row.event_type}</span>,
    },
    {
      header: "Processed Status",
      cell: (row) => (
        row.processed_at ? (
          <span className="badge badge-success">Processed</span>
        ) : (
          <span className="badge badge-warning">Received</span>
        )
      ),
    },
    {
      header: "Processed At",
      accessor: "processed_at",
      cell: (row) => <span>{row.processed_at ? new Date(row.processed_at).toLocaleString() : "Pending"}</span>,
    },
    {
      header: "Received At",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Quidax Broker Sync Monitor</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Monitor Quidax sub-account blockchain deposits, API payouts, and system webhook events.</p>
        </div>

        <button
          onClick={fetchQuidaxData}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Provider Logs
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {/* Tab Switcher Selector */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)", marginBottom: "var(--space-6)", gap: "var(--space-2)" }}>
        <button
          onClick={() => {
            setPage(1);
            setActiveTab("deposits");
          }}
          className={`btn ${activeTab === "deposits" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <ArrowDownLeft size={16} /> Sub-Account Deposits
        </button>
        <button
          onClick={() => {
            setPage(1);
            setActiveTab("withdrawals");
          }}
          className={`btn ${activeTab === "withdrawals" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <ArrowUpRight size={16} /> API Payout Withdrawals
        </button>
        <button
          onClick={() => {
            setPage(1);
            setActiveTab("webhooks");
          }}
          className={`btn ${activeTab === "webhooks" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <Activity size={16} /> Webhook Events Delivery
        </button>
      </div>

      {/* DataTables rendering */}
      {activeTab === "deposits" && (
        <DataTable
          columns={depositColumns}
          data={data?.deposits || []}
          loading={loading}
          meta={data?.deposits_meta}
          onPageChange={setPage}
          emptyMessage="No sub-account deposits found."
        />
      )}

      {activeTab === "withdrawals" && (
        <DataTable
          columns={withdrawalColumns}
          data={data?.withdrawals || []}
          loading={loading}
          meta={data?.withdrawals_meta}
          onPageChange={setPage}
          emptyMessage="No sub-account withdrawals found."
        />
      )}

      {activeTab === "webhooks" && (
        <DataTable
          columns={webhookColumns}
          data={data?.webhooks || []}
          loading={loading}
          emptyMessage="No provider webhooks received in this window."
        />
      )}
    </div>
  );
}
