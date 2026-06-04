"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import DataTable, { Column } from "../../components/DataTable";
import StatusBadge from "../../components/StatusBadge";
import Link from "next/link";
import { Search, Filter, RefreshCw, UserCheck } from "lucide-react";

interface UserListItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string | null;
  referral_code: string;
  kyc_status: string;
  is_active: boolean;
  is_staff: boolean;
  date_joined: string;
}

interface UserListResponse {
  users: UserListItem[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [meta, setMeta] = useState<UserListResponse["meta"] | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [kycStatus, setKycStatus] = useState("");
  const [isActive, setIsActive] = useState("");

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        page,
        page_size: 10,
      };
      if (search.trim()) params.search = search.trim();
      if (kycStatus) params.kyc_status = kycStatus;
      if (isActive !== "") params.is_active = isActive === "true";

      const res = await api.get<UserListResponse>("/admin/users", params);
      setUsers(res.users || []);
      setMeta(res.meta);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load user records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleClearFilters = () => {
    setSearch("");
    setKycStatus("");
    setIsActive("");
    setPage(1);
  };

  const columns: Column<UserListItem>[] = [
    {
      header: "Email",
      accessor: "email",
      cell: (row) => (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontWeight: 600 }}>{row.email}</span>
          {row.is_staff && (
            <span style={{ fontSize: "10px", color: "var(--blue)", fontWeight: 700, textTransform: "uppercase", marginTop: "2px" }}>
              Staff Account
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Name",
      cell: (row) => <span>{row.first_name} {row.last_name}</span>,
    },
    {
      header: "Phone",
      accessor: "phone_number",
      cell: (row) => <span>{row.phone_number || "—"}</span>,
    },
    {
      header: "KYC Status",
      accessor: "kyc_status",
      cell: (row) => <StatusBadge status={row.kyc_status} />,
    },
    {
      header: "Account State",
      accessor: "is_active",
      cell: (row) => (
        <span style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          color: row.is_active ? "var(--green-text)" : "var(--red-text)",
          fontWeight: 600
        }}>
          {row.is_active ? "Active" : "Suspended"}
        </span>
      ),
    },
    {
      header: "Joined Date",
      accessor: "date_joined",
      cell: (row) => <span>{new Date(row.date_joined).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}</span>,
    },
    {
      header: "Actions",
      cell: (row) => (
        <Link href={`/users/${row.id}`} className="btn btn-secondary btn-sm">
          Manage Account
        </Link>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">User Accounts</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Browse, filter, and audit platform user profiles and authentication access.</p>
        </div>

        <button
          onClick={fetchUsers}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Records
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {/* Filter Toolbar Card */}
      <div className="card">
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1, minWidth: "240px", marginBottom: 0 }}>
            <label className="form-label">Search Users</label>
            <div style={{ position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
              <input
                type="text"
                className="input"
                placeholder="Search by name, email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: "40px" }}
              />
            </div>
          </div>

          <div className="form-group" style={{ minWidth: "160px", marginBottom: 0 }}>
            <label className="form-label">KYC Verification</label>
            <select
              className="input select"
              value={kycStatus}
              onChange={(e) => setKycStatus(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="unverified">Unverified</option>
              <option value="submitted">Pending Review</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <div className="form-group" style={{ minWidth: "160px", marginBottom: 0 }}>
            <label className="form-label">Account Status</label>
            <select
              className="input select"
              value={isActive}
              onChange={(e) => setIsActive(e.target.value)}
            >
              <option value="">All States</option>
              <option value="true">Active Only</option>
              <option value="false">Suspended Only</option>
            </select>
          </div>

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

      {/* Users DataTable */}
      <DataTable
        columns={columns}
        data={users}
        loading={loading}
        meta={meta}
        onPageChange={setPage}
        emptyMessage="No users match the specified search or filter criteria."
      />
    </div>
  );
}
