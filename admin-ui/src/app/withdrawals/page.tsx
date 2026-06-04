"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import StatusBadge from "../../components/StatusBadge";
import Modal from "../../components/Modal";
import { RefreshCw, CheckCircle, XCircle, DollarSign, Wallet, Landmark } from "lucide-react";
import Link from "next/link";

interface WithdrawalItem {
  id: string;
  user_email: string;
  user_id: string;
  asset: string;
  amount: number;
  status: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  wallet_address: string;
  network: string;
  created_at: string;
}

interface WithdrawalListResponse {
  withdrawals: WithdrawalItem[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export default function WithdrawalsPage() {
  const [withdrawals, setWithdrawals] = useState<WithdrawalItem[]>([]);
  const [meta, setMeta] = useState<WithdrawalListResponse["meta"] | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("pending");

  // Actions
  const [selectedWd, setSelectedWd] = useState<WithdrawalItem | null>(null);
  const [isApproveOpen, setIsApproveOpen] = useState(false);
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [adminNotes, setAdminNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchWithdrawals = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        page,
        page_size: 20,
      };
      if (status) params.status = status;

      const res = await api.get<WithdrawalListResponse>("/admin/withdrawals", params);
      setWithdrawals(res.withdrawals || []);
      setMeta(res.meta);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to fetch withdrawal list.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWithdrawals();
  }, [page, status]);

  const handleApprove = async () => {
    if (!selectedWd) return;
    setSubmitting(true);
    try {
      await api.post(`/admin/withdrawals/${selectedWd.id}/approve`, {
        admin_notes: adminNotes || undefined,
      });
      setIsApproveOpen(false);
      setSelectedWd(null);
      setAdminNotes("");
      fetchWithdrawals();
    } catch (err: any) {
      alert(err.message || "Failed to approve withdrawal.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selectedWd) return;
    if (!rejectionReason.trim()) {
      alert("Please enter a rejection reason.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/admin/withdrawals/${selectedWd.id}/reject`, {
        rejection_reason: rejectionReason,
        admin_notes: adminNotes || undefined,
      });
      setIsRejectOpen(false);
      setSelectedWd(null);
      setRejectionReason("");
      setAdminNotes("");
      fetchWithdrawals();
    } catch (err: any) {
      alert(err.message || "Failed to reject withdrawal.");
    } finally {
      setSubmitting(false);
    }
  };

  const columns: Column<WithdrawalItem>[] = [
    {
      header: "User Account",
      accessor: "user_email",
      cell: (row) => (
        <Link href={`/users/${row.user_id}`} style={{ fontWeight: 600 }}>
          {row.user_email}
        </Link>
      ),
    },
    {
      header: "Asset",
      accessor: "asset",
      cell: (row) => <span style={{ fontWeight: 700 }}>{row.asset}</span>,
    },
    {
      header: "Amount",
      accessor: "amount",
      cell: (row) => (
        <span style={{ fontWeight: 600 }}>
          {row.asset === "USDT" || row.asset === "BTC" || row.asset === "ETH" ? "" : "₦"}
          {Number(row.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: "Payout Instructions",
      cell: (row) => {
        const isFiat = row.asset === "NGN";
        if (isFiat) {
          return (
            <div style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "12px" }}>
              <Landmark size={16} style={{ color: "var(--text-3)", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <div style={{ fontWeight: 600 }}>{row.bank_account_name}</div>
                <div style={{ color: "var(--text-2)" }}>{row.bank_name} • <span style={{ fontFamily: "monospace" }}>{row.bank_account_number}</span></div>
              </div>
            </div>
          );
        } else {
          return (
            <div style={{ display: "flex", gap: "8px", alignItems: "flex-start", fontSize: "12px" }}>
              <Wallet size={16} style={{ color: "var(--text-3)", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <div style={{ fontFamily: "monospace", wordBreak: "break-all", fontWeight: 500 }} title={row.wallet_address}>
                  {row.wallet_address.substring(0, 16)}...
                </div>
                <div style={{ color: "var(--text-2)", fontSize: "11px" }}>Network: <strong>{row.network}</strong></div>
              </div>
            </div>
          );
        }
      },
    },
    {
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Created Date",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
    {
      header: "Audit Actions",
      cell: (row) => (
        row.status === "pending" ? (
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              onClick={() => {
                setSelectedWd(row);
                setIsRejectOpen(true);
              }}
              className="btn btn-danger btn-sm"
            >
              Reject
            </button>
            <button
              onClick={() => {
                setSelectedWd(row);
                setIsApproveOpen(true);
              }}
              className="btn btn-success btn-sm"
            >
              Approve
            </button>
          </div>
        ) : (
          <span style={{ fontSize: "12px", color: "var(--text-3)" }}>
            Processed
          </span>
        )
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">User Withdrawals</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Audit and clear pending crypto/fiat payouts to customer external wallets and bank accounts.</p>
        </div>

        <button
          onClick={fetchWithdrawals}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Payouts
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {/* Filter toolbar card */}
      <div className="card">
        <div className="form-group" style={{ maxWidth: "240px", marginBottom: 0 }}>
          <label className="form-label font-bold">Payout Section</label>
          <select
            className="input select"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value);
            }}
          >
            <option value="pending">Pending Payouts (Recommended)</option>
            <option value="completed">Completed Payments</option>
            <option value="failed">Failed / Rejected Payouts</option>
            <option value="">All Withdrawals</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={withdrawals}
        loading={loading}
        meta={meta}
        onPageChange={setPage}
        emptyMessage="No withdrawals match the selected filters."
      />

      {/* APPROVE PAYOUT MODAL */}
      <Modal
        isOpen={isApproveOpen}
        onClose={() => {
          setIsApproveOpen(false);
          setSelectedWd(null);
          setAdminNotes("");
        }}
        title="Approve Withdrawal Payout"
        footer={
          <>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setIsApproveOpen(false);
                setSelectedWd(null);
                setAdminNotes("");
              }}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              className="btn btn-success"
              onClick={handleApprove}
              disabled={submitting}
            >
              {submitting ? "Processing..." : "Confirm & Send Funds"}
            </button>
          </>
        }
      >
        {selectedWd && (
          <div>
            <p style={{ fontSize: "13px", color: "var(--text-2)", marginBottom: "var(--space-4)" }}>
              You are approving withdrawal request for user <strong>{selectedWd.user_email}</strong>. Confirm that funds for <strong>{selectedWd.asset === "NGN" ? "₦" : ""}{Number(selectedWd.amount).toLocaleString()} {selectedWd.asset}</strong> have been disbursed or the bank transfer has been executed.
            </p>

            <div className="form-group">
              <label className="form-label font-bold">Transaction Reference / Staff Note</label>
              <textarea
                className="input"
                rows={3}
                placeholder="Paste transaction hashes, bank transfer logs or staff review remarks..."
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                style={{ resize: "vertical", minHeight: "80px" }}
              />
            </div>
          </div>
        )}
      </Modal>

      {/* REJECT PAYOUT MODAL */}
      <Modal
        isOpen={isRejectOpen}
        onClose={() => {
          setIsRejectOpen(false);
          setSelectedWd(null);
          setRejectionReason("");
          setAdminNotes("");
        }}
        title="Reject Withdrawal Payout"
        footer={
          <>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setIsRejectOpen(false);
                setSelectedWd(null);
                setRejectionReason("");
                setAdminNotes("");
              }}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              className="btn btn-danger"
              onClick={handleReject}
              disabled={submitting}
            >
              {submitting ? "Rejecting..." : "Confirm Rejection"}
            </button>
          </>
        }
      >
        {selectedWd && (
          <div>
            <p style={{ fontSize: "13px", color: "var(--text-2)", marginBottom: "var(--space-4)" }}>
              Reject withdrawal request for user <strong>{selectedWd.user_email}</strong> of <strong>{selectedWd.asset === "NGN" ? "₦" : ""}{Number(selectedWd.amount).toLocaleString()} {selectedWd.asset}</strong>. Rejected withdrawals will fail and lock balances can be rolled back.
            </p>

            <div className="form-group">
              <label className="form-label">Rejection Reason (Visible to User)</label>
              <input
                type="text"
                className="input"
                placeholder="e.g. Account name mismatch, incorrect banking details..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                required
              />
            </div>

            <div className="form-group" style={{ marginTop: "var(--space-4)" }}>
              <label className="form-label">Internal Audit Notes (Optional)</label>
              <textarea
                className="input"
                rows={3}
                placeholder="Staff notes for this rejection..."
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                style={{ resize: "vertical", minHeight: "80px" }}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
