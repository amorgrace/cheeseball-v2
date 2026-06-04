"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "../../../lib/api";
import StatusBadge from "../../../components/StatusBadge";
import Modal from "../../../components/Modal";
import Link from "next/link";
import {
  ChevronLeft,
  CheckCircle,
  XCircle,
  Clock,
  ArrowUpDown,
  CreditCard,
  Hash,
  AlertCircle,
  DollarSign,
  TrendingUp,
  Percent,
  Calendar,
  Layers,
  FileText
} from "lucide-react";

interface TransactionDetail {
  id: string;
  user_email: string;
  user_id: string;
  transaction_type: string;
  asset: string;
  status: string;
  payment_method: string | null;
  crypto_source: string;
  payout_method: string;
  naira_amount: number;
  crypto_amount: number;
  market_rate: number;
  markup_percent: number;
  final_rate: number;
  crypto_usd_price: number;
  wallet_address: string;
  network: string;
  broker_wallet_address: string;
  bank_name: string;
  bank_account_name: string;
  bank_account_number: string;
  admin_notes: string;
  rejection_reason: string;
  reviewed_at: string | null;
  paid_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  created_at: string;
  updated_at: string;
}

export default function TransactionDetailPage() {
  const { id } = useParams();
  const router = useRouter();

  const [txn, setTxn] = useState<TransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modals state
  const [isApproveOpen, setIsApproveOpen] = useState(false);
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [adminNotes, setAdminNotes] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchTransactionDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<TransactionDetail>(`/admin/transactions/${id}`);
      setTxn(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load transaction details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchTransactionDetails();
    }
  }, [id]);

  const handleApprove = async () => {
    if (!txn) return;
    setSubmitting(true);
    try {
      await api.post(`/admin/transactions/${txn.id}/approve`, {
        admin_notes: adminNotes || undefined,
      });
      setIsApproveOpen(false);
      setAdminNotes("");
      fetchTransactionDetails();
    } catch (err: any) {
      alert(err.message || "Failed to approve transaction.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!txn) return;
    if (!rejectionReason.trim()) {
      alert("Please provide a rejection reason.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/admin/transactions/${txn.id}/reject`, {
        rejection_reason: rejectionReason,
        admin_notes: adminNotes || undefined,
      });
      setIsRejectOpen(false);
      setRejectionReason("");
      setAdminNotes("");
      fetchTransactionDetails();
    } catch (err: any) {
      alert(err.message || "Failed to reject transaction.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "var(--space-12) 0", textAlign: "center" }}>
        <div className="skeleton" style={{ height: "40px", width: "300px", margin: "0 auto var(--space-4)", borderRadius: "var(--radius-md)" }} />
        <div className="skeleton" style={{ height: "300px", maxWidth: "900px", margin: "0 auto", borderRadius: "var(--radius-lg)" }} />
      </div>
    );
  }

  if (error || !txn) {
    return (
      <div className="card" style={{ background: "var(--red-light)", color: "var(--red-text)", textAlign: "center", padding: "var(--space-10)" }}>
        <h3>Error Auditing Transaction</h3>
        <p style={{ marginTop: "var(--space-2)" }}>{error || "The transaction record could not be found."}</p>
        <button onClick={() => router.push("/transactions")} className="btn btn-secondary" style={{ marginTop: "var(--space-4)" }}>
          Back to Transaction Audit
        </button>
      </div>
    );
  }

  const isPendingAction = txn.status === "pending_review" || txn.status === "paid";

  return (
    <div>
      {/* Navigation Header */}
      <div style={{ marginBottom: "var(--space-6)" }}>
        <Link href="/transactions" style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "13px", fontWeight: 600, color: "var(--text-2)", marginBottom: "var(--space-2)" }}>
          <ChevronLeft size={16} /> Back to Transaction Audit
        </Link>
        
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <h1 className="page-title">Transaction Audit Panel</h1>
              <StatusBadge status={txn.status} />
              <span className={`badge ${txn.transaction_type.toLowerCase() === "buy" ? "badge-success" : "badge-info"}`} style={{ textTransform: "uppercase" }}>
                {txn.transaction_type}
              </span>
            </div>
            <p style={{ color: "var(--text-2)", fontSize: "13px", marginTop: "2px" }}>ID: {txn.id}</p>
          </div>

          {isPendingAction && (
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <button
                onClick={() => setIsRejectOpen(true)}
                className="btn btn-danger"
              >
                <XCircle size={18} /> Reject Transaction
              </button>
              
              <button
                onClick={() => setIsApproveOpen(true)}
                className="btn btn-success"
              >
                <CheckCircle size={18} /> Approve Transaction
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="grid-cols-3">
        {/* Main calculation summary column */}
        <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
          
          {/* Core financial facts */}
          <div className="card" style={{ marginBottom: 0 }}>
            <h3 className="section-title">Financial Breakdown</h3>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-6)", marginTop: "var(--space-4)" }}>
              <div style={{ padding: "16px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Fiat Amount</div>
                <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--text)", marginTop: "4px" }}>
                  ₦{Number(txn.naira_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-2)", marginTop: "4px" }}>
                  Payment Method: <strong>{txn.payment_method || "Not Specified"}</strong>
                </div>
              </div>

              <div style={{ padding: "16px", background: "var(--blue-light)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
                <div style={{ fontSize: "11px", color: "var(--blue)", fontWeight: 600, textTransform: "uppercase" }}>Crypto Amount</div>
                <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--blue)", marginTop: "4px" }}>
                  {txn.crypto_amount} {txn.asset}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-2)", marginTop: "4px" }}>
                  Crypto Source: <strong>{txn.crypto_source.replace(/_/g, " ").toUpperCase()}</strong>
                </div>
              </div>
            </div>

            {/* Rates calculation specifications */}
            <div style={{ marginTop: "var(--space-6)" }}>
              <h4 style={{ fontSize: "13px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase", marginBottom: "var(--space-3)" }}>Exchange Rate Calculations</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-4)" }}>
                <div style={{ borderRight: "1px solid var(--border)", paddingRight: "12px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-2)" }}>Market Rate</div>
                  <div style={{ fontWeight: 700, fontSize: "15px", marginTop: "2px" }}>₦{Number(txn.market_rate).toLocaleString()}</div>
                </div>
                <div style={{ borderRight: "1px solid var(--border)", paddingRight: "12px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-2)" }}>Markup Applied</div>
                  <div style={{ fontWeight: 700, fontSize: "15px", marginTop: "2px", color: "var(--blue)" }}>{txn.markup_percent}%</div>
                </div>
                <div style={{ borderRight: "1px solid var(--border)", paddingRight: "12px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-2)" }}>Final Conversion Rate</div>
                  <div style={{ fontWeight: 700, fontSize: "15px", marginTop: "2px" }}>₦{Number(txn.final_rate).toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-2)" }}>Global Price (USD)</div>
                  <div style={{ fontWeight: 700, fontSize: "15px", marginTop: "2px" }}>${Number(txn.crypto_usd_price).toLocaleString()}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Settlement / Banking Instructions */}
          <div className="card" style={{ marginBottom: 0 }}>
            <h3 className="section-title">Settlement Details</h3>
            
            {txn.transaction_type.toLowerCase() === "buy" ? (
              // Buy means customer paid fiat, platform sends Crypto
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", marginTop: "var(--space-2)" }}>
                <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "14px", background: "var(--surface)" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Customer Destination Wallet Address</div>
                  <div style={{ fontFamily: "monospace", fontSize: "14px", fontWeight: 700, marginTop: "4px", color: "var(--text)", wordBreak: "break-all" }}>
                    {txn.wallet_address || "No address supplied"}
                  </div>
                  <div style={{ display: "flex", gap: "12px", marginTop: "8px", fontSize: "12px" }}>
                    <span>Network: <strong style={{ color: "var(--blue)" }}>{txn.network}</strong></span>
                  </div>
                </div>

                {txn.broker_wallet_address && (
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Broker Disbursement Account</span>
                    <div style={{ fontFamily: "monospace", fontSize: "13px", marginTop: "2px" }}>{txn.broker_wallet_address}</div>
                  </div>
                )}
              </div>
            ) : (
              // Sell means customer sends Crypto, platform pays NGN bank transfer
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", marginTop: "var(--space-2)" }}>
                <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "14px", background: "var(--surface)", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div style={{ gridColumn: "span 2" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Customer Bank Account Name</div>
                    <div style={{ fontSize: "15px", fontWeight: 700, marginTop: "2px" }}>{txn.bank_account_name || "—"}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Bank Name</div>
                    <div style={{ fontWeight: 600, marginTop: "2px" }}>{txn.bank_name || "—"}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Account Number</div>
                    <div style={{ fontWeight: 700, fontFamily: "monospace", fontSize: "15px", marginTop: "2px", color: "var(--blue)" }}>
                      {txn.bank_account_number || "—"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Audit Meta Side Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
          
          {/* Notes and Rejection details panel */}
          <div className="card" style={{ marginBottom: 0 }}>
            <h3 className="section-title">Audit Log Notes</h3>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", marginTop: "var(--space-2)" }}>
              <div>
                <span style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Staff Internal Notes</span>
                <div style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "10px", minHeight: "60px", background: "var(--surface)", fontSize: "13px", marginTop: "4px" }}>
                  {txn.admin_notes || <span style={{ color: "var(--text-3)" }}>No notes logged on this transaction.</span>}
                </div>
              </div>

              {txn.rejection_reason && (
                <div>
                  <span style={{ fontSize: "11px", color: "var(--red-text)", fontWeight: 600, textTransform: "uppercase" }}>Rejection Reason (Shown to User)</span>
                  <div style={{ border: "1px solid var(--red-light)", borderRadius: "var(--radius-md)", padding: "10px", background: "#FFF5F5", fontSize: "13px", color: "var(--red-text)", fontWeight: 500, marginTop: "4px" }}>
                    {txn.rejection_reason}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Platform Timeline */}
          <div className="card" style={{ marginBottom: 0 }}>
            <h3 className="section-title">Lifecycle Timeline</h3>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", marginTop: "var(--space-4)", position: "relative" }}>
              <div style={{ display: "flex", gap: "12px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--blue)" }} />
                  <div style={{ width: "2px", flex: 1, background: "var(--border)", margin: "4px 0" }} />
                </div>
                <div style={{ paddingBottom: "var(--space-2)" }}>
                  <div style={{ fontSize: "12px", fontWeight: 600 }}>Created & Quoted</div>
                  <div style={{ fontSize: "10px", color: "var(--text-2)", marginTop: "2px" }}>{new Date(txn.created_at).toLocaleString()}</div>
                </div>
              </div>

              {txn.paid_at && (
                <div style={{ display: "flex", gap: "12px" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--amber)" }} />
                    <div style={{ width: "2px", flex: 1, background: "var(--border)", margin: "4px 0" }} />
                  </div>
                  <div style={{ paddingBottom: "var(--space-2)" }}>
                    <div style={{ fontSize: "12px", fontWeight: 600 }}>Fiat Payment Verified</div>
                    <div style={{ fontSize: "10px", color: "var(--text-2)", marginTop: "2px" }}>{new Date(txn.paid_at).toLocaleString()}</div>
                  </div>
                </div>
              )}

              {txn.reviewed_at && (
                <div style={{ display: "flex", gap: "12px" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: "var(--blue-dark)" }} />
                    <div style={{ width: "2px", flex: 1, background: "var(--border)", margin: "4px 0" }} />
                  </div>
                  <div style={{ paddingBottom: "var(--space-2)" }}>
                    <div style={{ fontSize: "12px", fontWeight: 600 }}>Audited by Admin</div>
                    <div style={{ fontSize: "10px", color: "var(--text-2)", marginTop: "2px" }}>{new Date(txn.reviewed_at).toLocaleString()}</div>
                  </div>
                </div>
              )}

              <div style={{ display: "flex", gap: "12px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <div style={{
                    width: "10px",
                    height: "10px",
                    borderRadius: "50%",
                    background: txn.status === "completed" ? "var(--green)" : txn.status === "failed" || txn.status === "rejected" ? "var(--red)" : "var(--text-3)"
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: "12px", fontWeight: 600 }}>
                    {txn.status === "completed" ? "Completed" : txn.status === "failed" ? "Failed" : txn.status === "rejected" ? "Rejected" : "Pending Processing"}
                  </div>
                  {txn.completed_at && (
                    <div style={{ fontSize: "10px", color: "var(--text-2)", marginTop: "2px" }}>{new Date(txn.completed_at).toLocaleString()}</div>
                  )}
                  {txn.failed_at && (
                    <div style={{ fontSize: "10px", color: "var(--text-2)", marginTop: "2px" }}>{new Date(txn.failed_at).toLocaleString()}</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* APPROVAL MODAL */}
      <Modal
        isOpen={isApproveOpen}
        onClose={() => setIsApproveOpen(false)}
        title="Approve Transaction"
        footer={
          <>
            <button
              className="btn btn-secondary"
              onClick={() => setIsApproveOpen(false)}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              className="btn btn-success"
              onClick={handleApprove}
              disabled={submitting}
            >
              {submitting ? "Processing..." : "Confirm Approval"}
            </button>
          </>
        }
      >
        <p style={{ fontSize: "13px", color: "var(--text-2)", marginBottom: "var(--space-4)" }}>
          You are confirming that the fiat payment for <strong>₦{Number(txn.naira_amount).toLocaleString()}</strong> was received, or that this sell settlement is authorized. This will advance the transaction to the <strong>PROCESSING</strong> state.
        </p>
        <div className="form-group">
          <label className="form-label">Internal Audit Notes (Optional)</label>
          <textarea
            className="input"
            rows={3}
            placeholder="Add ledger remarks, broker logs or transfer references..."
            value={adminNotes}
            onChange={(e) => setAdminNotes(e.target.value)}
            style={{ resize: "vertical", minHeight: "80px" }}
          />
        </div>
      </Modal>

      {/* REJECTION MODAL */}
      <Modal
        isOpen={isRejectOpen}
        onClose={() => setIsRejectOpen(false)}
        title="Reject Transaction"
        footer={
          <>
            <button
              className="btn btn-secondary"
              onClick={() => setIsRejectOpen(false)}
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
        <p style={{ fontSize: "13px", color: "var(--text-2)", marginBottom: "var(--space-4)" }}>
          This will reject the transaction and log the reason. If it was a buy order, the transaction will mark as failed. Please explain the rejection clearly.
        </p>
        
        <div className="form-group">
          <label className="form-label">Rejection Reason (Required - Visible to User)</label>
          <input
            type="text"
            className="input"
            placeholder="e.g. Invalid bank receipt upload, incorrect wallet address..."
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
            placeholder="Additional staff-only observations..."
            value={adminNotes}
            onChange={(e) => setAdminNotes(e.target.value)}
            style={{ resize: "vertical", minHeight: "80px" }}
          />
        </div>
      </Modal>
    </div>
  );
}
