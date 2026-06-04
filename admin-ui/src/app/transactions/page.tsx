"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import StatusBadge from "../../components/StatusBadge";
import Link from "next/link";
import { Search, Filter, RefreshCw } from "lucide-react";

interface TransactionListItem {
  id: string;
  user_email: string;
  transaction_type: string;
  asset: string;
  status: string;
  payment_method: string | null;
  naira_amount: number;
  crypto_amount: number;
  final_rate: number;
  created_at: string;
}

interface TransactionListResponse {
  transactions: TransactionListItem[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<TransactionListItem[]>([]);
  const [meta, setMeta] = useState<TransactionListResponse["meta"] | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [txnType, setTxnType] = useState("");

  const fetchTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        page,
        page_size: 20,
      };
      if (search.trim()) params.search = search.trim();
      if (status) params.status = status;
      if (txnType) params.transaction_type = txnType;

      const res = await api.get<TransactionListResponse>("/admin/transactions", params);
      setTransactions(res.transactions || []);
      setMeta(res.meta);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load transaction logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [page]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTransactions();
  };

  const handleClearFilters = () => {
    setSearch("");
    setStatus("");
    setTxnType("");
    setPage(1);
  };

  const columns: Column<TransactionListItem>[] = [
    {
      header: "Transaction ID",
      accessor: "id",
      cell: (row) => <span style={{ fontFamily: "monospace", fontSize: "12px", fontWeight: 600 }}>{row.id.substring(0, 8)}...</span>,
    },
    {
      header: "User",
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
      header: "Naira Amount",
      accessor: "naira_amount",
      cell: (row) => <span>₦{Number(row.naira_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>,
    },
    {
      header: "Crypto Amount",
      accessor: "crypto_amount",
      cell: (row) => <span>{row.crypto_amount} {row.asset}</span>,
    },
    {
      header: "Rate",
      accessor: "final_rate",
      cell: (row) => <span>₦{Number(row.final_rate).toLocaleString()}</span>,
    },
    {
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Date Created",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
    {
      header: "Actions",
      cell: (row) => (
        <Link href={`/transactions/${row.id}`} className="btn btn-secondary btn-sm">
          Audit Detail
        </Link>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Transaction Audit</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Monitor and moderate user cryptocurrency purchase and sale transactions.</p>
        </div>

        <button
          onClick={fetchTransactions}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Transactions
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {/* Filters Toolbar Card */}
      <div className="card">
        <form onSubmit={handleFilterSubmit} style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1, minWidth: "240px", marginBottom: 0 }}>
            <label className="form-label">Search Query</label>
            <div style={{ position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
              <input
                type="text"
                className="input"
                placeholder="Search by User Email, ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: "40px" }}
              />
            </div>
          </div>

          <div className="form-group" style={{ minWidth: "160px", marginBottom: 0 }}>
            <label className="form-label">Transaction Type</label>
            <select
              className="input select"
              value={txnType}
              onChange={(e) => setTxnType(e.target.value)}
            >
              <option value="">All Types</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </div>

          <div className="form-group" style={{ minWidth: "180px", marginBottom: 0 }}>
            <label className="form-label">Audit Status</label>
            <select
              className="input select"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="pending_payment">Pending Payment</option>
              <option value="pending_review">Pending Review</option>
              <option value="paid">Paid</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button type="submit" className="btn btn-primary" style={{ height: "40px" }}>
              Apply filters
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClearFilters}
              style={{ height: "40px" }}
            >
              Clear
            </button>
          </div>
        </form>
      </div>

      {/* DataTable */}
      <DataTable
        columns={columns}
        data={transactions}
        loading={loading}
        meta={meta}
        onPageChange={setPage}
        emptyMessage="No transaction logs match the specified filters."
      />
    </div>
  );
}
