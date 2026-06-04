"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import StatusBadge from "../../components/StatusBadge";
import Modal from "../../components/Modal";
import { RefreshCw, FileText, CheckCircle, XCircle, ExternalLink } from "lucide-react";
import Link from "next/link";

interface KYCSubmissionItem {
  id: string;
  user_email: string;
  user_id: string;
  id_type: string;
  document_url: string;
  status: string;
  admin_note: string;
  reviewed_at: string | null;
  created_at: string;
}

interface KYCListResponse {
  submissions: KYCSubmissionItem[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export default function KYCPage() {
  const [submissions, setSubmissions] = useState<KYCSubmissionItem[]>([]);
  const [meta, setMeta] = useState<KYCListResponse["meta"] | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("submitted"); // default to pending submissions

  // Action states
  const [selectedSub, setSelectedSub] = useState<KYCSubmissionItem | null>(null);
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [isDocumentOpen, setIsDocumentOpen] = useState(false);
  const [adminNote, setAdminNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchKYC = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        page,
        page_size: 20,
      };
      if (status) params.status = status;

      const res = await api.get<KYCListResponse>("/admin/kyc", params);
      setSubmissions(res.submissions || []);
      setMeta(res.meta);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to fetch KYC submissions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKYC();
  }, [page, status]);

  const handleReview = async (action: "approve" | "reject") => {
    if (!selectedSub) return;
    if (action === "reject" && !adminNote.trim()) {
      alert("Please provide a rejection note explaining the reason.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/admin/kyc/${selectedSub.id}/review`, {
        action,
        admin_note: adminNote || undefined,
      });
      setIsReviewOpen(false);
      setSelectedSub(null);
      setAdminNote("");
      fetchKYC();
    } catch (err: any) {
      alert(err.message || "Failed to submit review.");
    } finally {
      setSubmitting(false);
    }
  };

  const columns: Column<KYCSubmissionItem>[] = [
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
      header: "Document Type",
      accessor: "id_type",
      cell: (row) => <span style={{ fontWeight: 600, textTransform: "uppercase" }}>{row.id_type}</span>,
    },
    {
      header: "File Attachment",
      cell: (row) => (
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            onClick={() => {
              setSelectedSub(row);
              setIsDocumentOpen(true);
            }}
            className="btn btn-secondary btn-sm"
            style={{ display: "inline-flex", gap: "4px" }}
          >
            <FileText size={14} /> Preview
          </button>
          
          <a
            href={row.document_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: "inline-flex", alignItems: "center", fontSize: "12px", color: "var(--blue)" }}
            title="Open file in new tab"
          >
            Open <ExternalLink size={12} style={{ marginLeft: "2px" }} />
          </a>
        </div>
      ),
    },
    {
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Submitted Date",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
    {
      header: "Review Actions",
      cell: (row) => (
        row.status === "submitted" ? (
          <button
            onClick={() => {
              setSelectedSub(row);
              setIsReviewOpen(true);
            }}
            className="btn btn-primary btn-sm"
          >
            Review Submission
          </button>
        ) : (
          <span style={{ fontSize: "12px", color: "var(--text-3)" }}>
            Audited
          </span>
        )
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">KYC Review Queue</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Verify customer identity documentation uploads to comply with financial protocols.</p>
        </div>

        <button
          onClick={fetchKYC}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Queue
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
          <label className="form-label font-bold">Queue Section</label>
          <select
            className="input select"
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value);
            }}
          >
            <option value="submitted">Pending Review (Recommended)</option>
            <option value="verified">Verified Documents</option>
            <option value="rejected">Rejected Documents</option>
            <option value="">All Document Uploads</option>
          </select>
        </div>
      </div>

      {/* Queue DataTable */}
      <DataTable
        columns={columns}
        data={submissions}
        loading={loading}
        meta={meta}
        onPageChange={setPage}
        emptyMessage="No verification submissions matching this filter in the queue."
      />

      {/* PREVIEW DOCUMENT MODAL */}
      <Modal
        isOpen={isDocumentOpen}
        onClose={() => {
          setIsDocumentOpen(false);
          setSelectedSub(null);
        }}
        title={`KYC Document Preview - ${selectedSub?.id_type.toUpperCase()}`}
        maxWidth="640px"
      >
        {selectedSub && (
          <div>
            <div style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "var(--space-4)",
              textAlign: "center",
              minHeight: "300px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
              marginBottom: "var(--space-4)"
            }}>
              {/* If document is image, render it, else show fallback link */}
              {selectedSub.document_url.match(/\.(jpeg|jpg|gif|png|webp)/i) ? (
                <img
                  src={selectedSub.document_url}
                  alt="KYC Document Preview"
                  style={{ maxWidth: "100%", maxHeight: "400px", objectFit: "contain", borderRadius: "var(--radius-md)" }}
                />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
                  <FileText size={48} style={{ color: "var(--text-3)" }} />
                  <p style={{ fontWeight: 600, color: "var(--text-2)" }}>PDF or Binary Document Type</p>
                  <a
                    href={selectedSub.document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{ display: "inline-flex", gap: "4px" }}
                  >
                    Open Document in New Tab <ExternalLink size={16} />
                  </a>
                </div>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "13px" }}>
              <div>
                <span style={{ color: "var(--text-2)", fontWeight: 600 }}>USER EMAIL</span>
                <div style={{ fontWeight: 700 }}>{selectedSub.user_email}</div>
              </div>
              <div>
                <span style={{ color: "var(--text-2)", fontWeight: 600 }}>SUBMITTED DATE</span>
                <div style={{ fontWeight: 700 }}>{new Date(selectedSub.created_at).toLocaleString()}</div>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* REVIEW ACTION MODAL */}
      <Modal
        isOpen={isReviewOpen}
        onClose={() => {
          setIsReviewOpen(false);
          setSelectedSub(null);
          setAdminNote("");
        }}
        title="Audit KYC Document Upload"
        footer={
          <>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setIsReviewOpen(false);
                setSelectedSub(null);
                setAdminNote("");
              }}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              className="btn btn-danger"
              onClick={() => handleReview("reject")}
              disabled={submitting}
            >
              <XCircle size={14} /> Reject Upload
            </button>
            <button
              className="btn btn-success"
              onClick={() => handleReview("approve")}
              disabled={submitting}
            >
              <CheckCircle size={14} /> Approve & Verify
            </button>
          </>
        }
      >
        {selectedSub && (
          <div>
            <p style={{ fontSize: "13px", color: "var(--text-2)", marginBottom: "var(--space-4)" }}>
              Confirm your audit review for user <strong>{selectedSub.user_email}</strong>. Check that the document type (<strong>{selectedSub.id_type.toUpperCase()}</strong>) and the file upload match user credentials.
            </p>

            <div className="form-group">
              <label className="form-label">Review Remarks / Audit Note</label>
              <textarea
                className="input"
                rows={3}
                placeholder="Include approval remarks or rejection grounds (required on rejection)..."
                value={adminNote}
                onChange={(e) => setAdminNote(e.target.value)}
                style={{ resize: "vertical", minHeight: "80px" }}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
