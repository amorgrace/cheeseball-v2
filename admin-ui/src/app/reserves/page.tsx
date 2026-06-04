"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import { RefreshCw, Coins, ArrowUpDown, History } from "lucide-react";

interface ReserveItem {
  asset_code: string;
  balance: number;
  updated_at: string;
}

interface ReserveMovementItem {
  asset_code: string;
  movement_type: string;
  amount: number;
  notes: string;
  created_at: string;
}

interface ReservesResponse {
  reserves: ReserveItem[];
  movements: ReserveMovementItem[];
}

export default function ReservesPage() {
  const [reserves, setReserves] = useState<ReserveItem[]>([]);
  const [movements, setMovements] = useState<ReserveMovementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReserves = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<ReservesResponse>("/admin/reserves");
      setReserves(res.reserves || []);
      setMovements(res.movements || []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load reserves audit log.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReserves();
  }, []);

  const movementColumns: Column<ReserveMovementItem>[] = [
    {
      header: "Asset",
      accessor: "asset_code",
      cell: (row) => <span style={{ fontWeight: 700 }}>{row.asset_code}</span>,
    },
    {
      header: "Movement Type",
      accessor: "movement_type",
      cell: (row) => (
        <span style={{
          textTransform: "uppercase",
          fontSize: "11px",
          fontWeight: 700,
          color: row.movement_type.toLowerCase() === "deposit" || row.movement_type.toLowerCase() === "in" ? "var(--green-text)" : "var(--red-text)"
        }}>
          {row.movement_type.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      header: "Amount",
      accessor: "amount",
      cell: (row) => (
        <span style={{ fontWeight: 600 }}>
          {Number(row.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: "Remarks / Notes",
      accessor: "notes",
      cell: (row) => <span style={{ fontSize: "12px", color: "var(--text-2)" }}>{row.notes}</span>,
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
          <h1 className="page-title">Platform Reserves</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Track cumulative platform vault reserve balances and asset flow movements.</p>
        </div>

        <button
          onClick={fetchReserves}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Reserves
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {/* Reserves Balances Grid */}
      <h3 className="section-title">Vault Reserve Balances</h3>
      {loading ? (
        <div className="grid-cols-4" style={{ marginBottom: "var(--space-6)" }}>
          {Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className="skeleton" style={{ height: "120px", borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      ) : reserves.length === 0 ? (
        <div className="card" style={{ marginBottom: "var(--space-6)" }}>
          <p style={{ color: "var(--text-3)" }}>No platform reserve vaults recorded.</p>
        </div>
      ) : (
        <div className="grid-cols-4" style={{ marginBottom: "var(--space-6)" }}>
          {reserves.map((res) => (
            <div key={res.asset_code} className="stats-card">
              <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-1)" }}>
                <span className="label" style={{ fontWeight: 700 }}>{res.asset_code} Vault</span>
                <Coins size={18} style={{ color: "var(--blue)" }} />
              </div>
              <div className="value">
                {res.asset_code === "USDT" || res.asset_code === "BTC" || res.asset_code === "ETH" ? "" : "₦"}
                {Number(res.balance).toLocaleString()}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-3)", marginTop: "var(--space-1)" }}>
                Last updated: {new Date(res.updated_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reserve Movement Logs */}
      <div className="card">
        <h3 className="section-title">Recent Movement Logs</h3>
        <DataTable
          columns={movementColumns}
          data={movements}
          loading={loading}
          emptyMessage="No reserve movement history logs exist."
        />
      </div>
    </div>
  );
}
