"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import { RefreshCw, Search, Wallet, ClipboardList } from "lucide-react";

interface WalletItem {
  id: string;
  user_email: string;
  user_id: string;
  asset: string;
  balance: number;
  locked_balance: number;
  available_balance: number;
  updated_at: string;
}

interface LedgerItem {
  id: string;
  user_email: string;
  asset: string;
  transaction_type: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  locked_before: number;
  locked_after: number;
  reference_id: string | null;
  reference_model: string;
  notes: string;
  created_at: string;
}

interface WalletsResponse {
  wallets: WalletItem[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

interface LedgerResponse {
  entries: LedgerItem[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export default function WalletsPage() {
  const [activeTab, setActiveTab] = useState<"balances" | "ledger">("balances");
  const [wallets, setWallets] = useState<WalletItem[]>([]);
  const [ledger, setLedger] = useState<LedgerItem[]>([]);
  
  const [walletsMeta, setWalletsMeta] = useState<WalletsResponse["meta"] | undefined>(undefined);
  const [ledgerMeta, setLedgerMeta] = useState<LedgerResponse["meta"] | undefined>(undefined);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [search, setSearch] = useState("");
  const [assetFilter, setAssetFilter] = useState("");
  const [ledgerTypeFilter, setLedgerTypeFilter] = useState("");
  const [page, setPage] = useState(1);

  const fetchWalletsData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "balances") {
        const params: any = { page, page_size: 20 };
        if (search.trim()) params.search = search.trim();
        if (assetFilter) params.asset = assetFilter;
        
        const res = await api.get<WalletsResponse>("/admin/wallets", params);
        setWallets(res.wallets || []);
        setWalletsMeta(res.meta);
      } else {
        const params: any = { page, page_size: 20 };
        if (search.trim()) params.search = search.trim();
        if (ledgerTypeFilter) params.transaction_type = ledgerTypeFilter;

        const res = await api.get<LedgerResponse>("/admin/ledger", params);
        setLedger(res.entries || []);
        setLedgerMeta(res.meta);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load wallet ledger data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWalletsData();
  }, [activeTab, page]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchWalletsData();
  };

  const handleClearFilters = () => {
    setSearch("");
    setAssetFilter("");
    setLedgerTypeFilter("");
    setPage(1);
  };

  const walletColumns: Column<WalletItem>[] = [
    {
      header: "User Account",
      accessor: "user_email",
      cell: (row) => <span style={{ fontWeight: 600 }}>{row.user_email}</span>,
    },
    {
      header: "Asset",
      accessor: "asset",
      cell: (row) => <span style={{ fontWeight: 700 }}>{row.asset}</span>,
    },
    {
      header: "Total Balance",
      accessor: "balance",
      cell: (row) => <span>{Number(row.balance).toLocaleString()}</span>,
    },
    {
      header: "Locked Balance",
      accessor: "locked_balance",
      cell: (row) => <span style={{ color: "var(--text-3)" }}>{Number(row.locked_balance).toLocaleString()}</span>,
    },
    {
      header: "Available Balance",
      accessor: "available_balance",
      cell: (row) => <span style={{ color: "var(--blue)", fontWeight: 600 }}>{Number(row.available_balance).toLocaleString()}</span>,
    },
    {
      header: "Last Updated",
      accessor: "updated_at",
      cell: (row) => <span>{new Date(row.updated_at).toLocaleString()}</span>,
    },
  ];

  const ledgerColumns: Column<LedgerItem>[] = [
    {
      header: "User Account",
      accessor: "user_email",
      cell: (row) => <span style={{ fontWeight: 600 }}>{row.user_email}</span>,
    },
    {
      header: "Asset",
      accessor: "asset",
      cell: (row) => <span style={{ fontWeight: 700 }}>{row.asset}</span>,
    },
    {
      header: "Action Type",
      accessor: "transaction_type",
      cell: (row) => <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>{row.transaction_type.replace(/_/g, " ")}</span>,
    },
    {
      header: "Delta Amount",
      accessor: "amount",
      cell: (row) => (
        <span style={{ color: Number(row.amount) >= 0 ? "var(--green-text)" : "var(--red-text)", fontWeight: 600 }}>
          {Number(row.amount) >= 0 ? "+" : ""}
          {Number(row.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: "Balance Change",
      cell: (row) => (
        <span style={{ fontSize: "12px", color: "var(--text-2)" }}>
          {Number(row.balance_before).toLocaleString()} → {Number(row.balance_after).toLocaleString()}
        </span>
      ),
    },
    {
      header: "Remarks / Notes",
      accessor: "notes",
      cell: (row) => <span style={{ fontSize: "12px", color: "var(--text-2)" }} title={row.notes}>{row.notes}</span>,
    },
    {
      header: "Recorded At",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">User Wallets & Ledgers</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Browse customer account balances and audit the global double-entry transactional journal.</p>
        </div>

        <button
          onClick={fetchWalletsData}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Ledger
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
            setActiveTab("balances");
          }}
          className={`btn ${activeTab === "balances" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <Wallet size={16} /> Wallet Balances
        </button>
        <button
          onClick={() => {
            setPage(1);
            setActiveTab("ledger");
          }}
          className={`btn ${activeTab === "ledger" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <ClipboardList size={16} /> Ledger Journal
        </button>
      </div>

      {/* Filter toolbar card */}
      <div className="card">
        <form onSubmit={handleFilterSubmit} style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1, minWidth: "240px", marginBottom: 0 }}>
            <label className="form-label">Search User Email</label>
            <div style={{ position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
              <input
                type="text"
                className="input"
                placeholder="Search by customer email address..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: "40px" }}
              />
            </div>
          </div>

          {activeTab === "balances" ? (
            <div className="form-group" style={{ minWidth: "160px", marginBottom: 0 }}>
              <label className="form-label">Filter Asset</label>
              <select
                className="input select"
                value={assetFilter}
                onChange={(e) => setAssetFilter(e.target.value)}
              >
                <option value="">All Assets</option>
                <option value="NGN">NGN (Fiat)</option>
                <option value="USDT">USDT (Tether)</option>
                <option value="BTC">BTC (Bitcoin)</option>
                <option value="ETH">ETH (Ethereum)</option>
              </select>
            </div>
          ) : (
            <div className="form-group" style={{ minWidth: "180px", marginBottom: 0 }}>
              <label className="form-label">Action Log Type</label>
              <select
                className="input select"
                value={ledgerTypeFilter}
                onChange={(e) => setLedgerTypeFilter(e.target.value)}
              >
                <option value="">All Actions</option>
                <option value="deposit">Deposit</option>
                <option value="withdrawal">Withdrawal</option>
                <option value="buy">Crypto Purchase</option>
                <option value="sell">Crypto Sale</option>
                <option value="referral_bonus">Referral Reward</option>
                <option value="manual_adjustment">Admin Adjustment</option>
              </select>
            </div>
          )}

          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button type="submit" className="btn btn-primary" style={{ height: "40px" }}>
              Apply Filters
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
      {activeTab === "balances" ? (
        <DataTable
          columns={walletColumns}
          data={wallets}
          loading={loading}
          meta={walletsMeta}
          onPageChange={setPage}
          emptyMessage="No wallet balances found matching the filters."
        />
      ) : (
        <DataTable
          columns={ledgerColumns}
          data={ledger}
          loading={loading}
          meta={ledgerMeta}
          onPageChange={setPage}
          emptyMessage="No ledger journal logs match the specified criteria."
        />
      )}
    </div>
  );
}
