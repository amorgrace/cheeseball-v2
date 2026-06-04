"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "../../../lib/api";
import StatusBadge from "../../../components/StatusBadge";
import DataTable, { Column } from "../../../components/DataTable";
import Link from "next/link";
import {
  User,
  ShieldAlert,
  Wallet,
  ArrowUpDown,
  History,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ToggleLeft,
  ToggleRight,
  Mail,
  Phone,
  Calendar,
  Gift
} from "lucide-react";

interface UserDetail {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string | null;
  referral_code: string;
  referred_by_email: string | null;
  referral_count: number;
  kyc_status: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  verified_at: string | null;
  date_joined: string;
  last_login: string | null;
}

interface WalletItem {
  id: string;
  asset: string;
  balance: number;
  locked_balance: number;
  available_balance: number;
}

interface TransactionItem {
  id: string;
  transaction_type: string;
  asset: string;
  status: string;
  naira_amount: number;
  crypto_amount: number;
  final_rate: number;
  created_at: string;
}

interface LedgerItem {
  id: string;
  asset: string;
  transaction_type: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  notes: string;
  created_at: string;
}

export default function UserDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  
  const [user, setUser] = useState<UserDetail | null>(null);
  const [wallets, setWallets] = useState<WalletItem[]>([]);
  const [txns, setTxns] = useState<TransactionItem[]>([]);
  const [ledger, setLedger] = useState<LedgerItem[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "txns" | "ledger">("profile");

  const fetchUserDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch main user details
      const userRes = await api.get<UserDetail>(`/admin/users/${id}`);
      setUser(userRes);

      // 2. Fetch user's wallets using search query
      const walletsRes = await api.get<{ wallets: WalletItem[] }>("/admin/wallets", {
        search: userRes.email,
        page_size: 50,
      });
      setWallets(walletsRes.wallets || []);

      // 3. Fetch user's transactions using search query
      const txnsRes = await api.get<{ transactions: TransactionItem[] }>("/admin/transactions", {
        search: userRes.email,
        page_size: 50,
      });
      setTxns(txnsRes.transactions || []);

      // 4. Fetch user's ledger entries using search query
      const ledgerRes = await api.get<{ entries: LedgerItem[] }>("/admin/ledger", {
        search: userRes.email,
        page_size: 50,
      });
      setLedger(ledgerRes.entries || []);

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load user details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchUserDetails();
    }
  }, [id]);

  const handleToggleActive = async () => {
    if (!user) return;
    setUpdating(true);
    try {
      const nextActive = !user.is_active;
      await api.patch(`/admin/users/${user.id}`, { is_active: nextActive });
      setUser({ ...user, is_active: nextActive });
    } catch (err: any) {
      alert(err.message || "Failed to update user active status.");
    } finally {
      setUpdating(false);
    }
  };

  const handleUpdateKycStatus = async (status: string) => {
    if (!user) return;
    if (!confirm(`Are you sure you want to change this user's KYC status to ${status.toUpperCase()}?`)) return;
    setUpdating(true);
    try {
      await api.patch(`/admin/users/${user.id}`, { kyc_status: status });
      setUser({ ...user, kyc_status: status });
    } catch (err: any) {
      alert(err.message || "Failed to update user KYC status.");
    } finally {
      setUpdating(false);
    }
  };

  const txnColumns: Column<TransactionItem>[] = [
    {
      header: "Txn ID",
      accessor: "id",
      cell: (row) => <span style={{ fontFamily: "monospace", fontSize: "12px" }}>{row.id.substring(0, 8)}...</span>,
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
      header: "Status",
      accessor: "status",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "Created At",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
    {
      header: "Action",
      cell: (row) => (
        <Link href={`/transactions/${row.id}`} className="btn btn-secondary btn-sm">
          View Details
        </Link>
      ),
    },
  ];

  const ledgerColumns: Column<LedgerItem>[] = [
    {
      header: "Asset",
      accessor: "asset",
    },
    {
      header: "Action Type",
      accessor: "transaction_type",
      cell: (row) => <span style={{ textTransform: "uppercase", fontSize: "11px", fontWeight: 700 }}>{row.transaction_type.replace(/_/g, " ")}</span>,
    },
    {
      header: "Amount",
      accessor: "amount",
      cell: (row) => (
        <span style={{ color: Number(row.amount) >= 0 ? "var(--green-text)" : "var(--red-text)", fontWeight: 600 }}>
          {Number(row.amount) >= 0 ? "+" : ""}
          {Number(row.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: "Balance Before",
      accessor: "balance_before",
      cell: (row) => <span>{Number(row.balance_before).toLocaleString()}</span>,
    },
    {
      header: "Balance After",
      accessor: "balance_after",
      cell: (row) => <span>{Number(row.balance_after).toLocaleString()}</span>,
    },
    {
      header: "Notes",
      accessor: "notes",
      cell: (row) => <span style={{ fontSize: "12px", color: "var(--text-2)" }}>{row.notes}</span>,
    },
    {
      header: "Recorded At",
      accessor: "created_at",
      cell: (row) => <span>{new Date(row.created_at).toLocaleString()}</span>,
    },
  ];

  if (loading) {
    return (
      <div style={{ padding: "var(--space-12) 0", textAlign: "center" }}>
        <div className="skeleton" style={{ height: "40px", width: "300px", margin: "0 auto var(--space-4)", borderRadius: "var(--radius-md)" }} />
        <div className="skeleton" style={{ height: "200px", maxWidth: "800px", margin: "0 auto", borderRadius: "var(--radius-lg)" }} />
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="card" style={{ background: "var(--red-light)", color: "var(--red-text)", textAlign: "center", padding: "var(--space-10)" }}>
        <h3>Error Accessing User File</h3>
        <p style={{ marginTop: "var(--space-2)" }}>{error || "The user record could not be located."}</p>
        <button onClick={() => router.push("/users")} className="btn btn-secondary" style={{ marginTop: "var(--space-4)" }}>
          Back to User Accounts
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Navigation Header */}
      <div style={{ marginBottom: "var(--space-6)" }}>
        <Link href="/users" style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "13px", fontWeight: 600, color: "var(--text-2)", marginBottom: "var(--space-2)" }}>
          <ChevronLeft size={16} /> Back to Users list
        </Link>
        
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <h1 className="page-title">{user.first_name} {user.last_name}</h1>
              <StatusBadge status={user.kyc_status} />
              {!user.is_active && <span className="badge badge-error">Suspended</span>}
            </div>
            <p style={{ color: "var(--text-2)", fontSize: "13px", marginTop: "2px" }}>ID: {user.id}</p>
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button
              onClick={handleToggleActive}
              className={`btn ${user.is_active ? "btn-danger" : "btn-success"}`}
              disabled={updating}
            >
              {user.is_active ? <ToggleLeft size={18} /> : <ToggleRight size={18} />}
              {user.is_active ? "Suspend Account" : "Reactivate Account"}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs Selector */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)", marginBottom: "var(--space-6)", gap: "var(--space-2)" }}>
        <button
          onClick={() => setActiveTab("profile")}
          className={`btn ${activeTab === "profile" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <User size={16} /> Profile & Balances
        </button>
        <button
          onClick={() => setActiveTab("txns")}
          className={`btn ${activeTab === "txns" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <ArrowUpDown size={16} /> Transactions ({txns.length})
        </button>
        <button
          onClick={() => setActiveTab("ledger")}
          className={`btn ${activeTab === "ledger" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderBottomLeftRadius: 0, borderBottomRightRadius: 0, padding: "10px 20px" }}
        >
          <History size={16} /> Ledger Log ({ledger.length})
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === "profile" && (
        <div className="grid-cols-3">
          {/* Column 1 & 2: User details and Wallets */}
          <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
            
            {/* Profile Information */}
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 className="section-title">Profile Specifications</h3>
              
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginTop: "var(--space-2)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Mail size={16} style={{ color: "var(--text-3)" }} />
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Email Address</div>
                    <div style={{ fontWeight: 600 }}>{user.email}</div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Phone size={16} style={{ color: "var(--text-3)" }} />
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Phone Number</div>
                    <div style={{ fontWeight: 600 }}>{user.phone_number || "Not provided"}</div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Calendar size={16} style={{ color: "var(--text-3)" }} />
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Joined Platform</div>
                    <div style={{ fontWeight: 600 }}>{new Date(user.date_joined).toLocaleString()}</div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Calendar size={16} style={{ color: "var(--text-3)" }} />
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Last Signed In</div>
                    <div style={{ fontWeight: 600 }}>{user.last_login ? new Date(user.last_login).toLocaleString() : "Never"}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Wallet Balances list */}
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 className="section-title">Asset Balances</h3>
              {wallets.length === 0 ? (
                <p style={{ color: "var(--text-3)" }}>No wallet balance profiles active for this account.</p>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "var(--space-4)" }}>
                  {wallets.map((wallet) => (
                    <div key={wallet.id} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "12px", background: "var(--surface)", display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 700, fontSize: "16px", color: "var(--text)" }}>{wallet.asset}</span>
                        <Wallet size={16} style={{ color: "var(--text-3)" }} />
                      </div>
                      <div>
                        <div style={{ fontSize: "10px", color: "var(--text-2)", textTransform: "uppercase", fontWeight: 600 }}>Available Balance</div>
                        <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--blue)" }}>
                          {wallet.asset === "USDT" || wallet.asset === "BTC" || wallet.asset === "ETH" ? "" : "₦"}
                          {Number(wallet.available_balance).toLocaleString()}
                        </div>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-2)", borderTop: "1px solid var(--border)", paddingTop: "4px", marginTop: "4px" }}>
                        <span>Locked:</span>
                        <span>{Number(wallet.locked_balance).toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Column 3: KYC and referral stats */}
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
            
            {/* Direct KYC override panel */}
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 className="section-title">Verification Override</h3>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                <button
                  onClick={() => handleUpdateKycStatus("verified")}
                  className="btn btn-success"
                  style={{ width: "100%" }}
                  disabled={updating || user.kyc_status === "verified"}
                >
                  <CheckCircle size={16} /> Force Verify KYC
                </button>
                
                <button
                  onClick={() => handleUpdateKycStatus("rejected")}
                  className="btn btn-danger"
                  style={{ width: "100%" }}
                  disabled={updating || user.kyc_status === "rejected"}
                >
                  <XCircle size={16} /> Force Reject KYC
                </button>

                <button
                  onClick={() => handleUpdateKycStatus("unverified")}
                  className="btn btn-secondary"
                  style={{ width: "100%" }}
                  disabled={updating || user.kyc_status === "unverified"}
                >
                  Reset to Unverified
                </button>
              </div>
            </div>

            {/* Referrals Stats Card */}
            <div className="card" style={{ marginBottom: 0 }}>
              <h3 className="section-title">Referral Ledger</h3>
              <div style={{ display: "flex", alignItems: "center", gap: "12px", background: "var(--surface)", padding: "14px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", marginBottom: "var(--space-3)" }}>
                <Gift size={24} style={{ color: "var(--blue)" }} />
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Referrals Recruited</div>
                  <div style={{ fontSize: "20px", fontWeight: 700 }}>{user.referral_count} users</div>
                </div>
              </div>
              
              <div>
                <span style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Personal Referral Code</span>
                <div style={{ fontSize: "15px", fontWeight: 700, background: "var(--blue-light)", color: "var(--blue)", padding: "6px 12px", borderRadius: "var(--radius-sm)", display: "inline-block", marginTop: "4px", fontFamily: "monospace", letterSpacing: "1px" }}>
                  {user.referral_code}
                </div>
              </div>
              
              {user.referred_by_email && (
                <div style={{ marginTop: "var(--space-3)", borderTop: "1px solid var(--border)", paddingTop: "var(--space-3)" }}>
                  <span style={{ fontSize: "11px", color: "var(--text-2)", fontWeight: 600, textTransform: "uppercase" }}>Invited By Sponsor</span>
                  <div style={{ fontWeight: 600, fontSize: "13px", marginTop: "2px" }}>{user.referred_by_email}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === "txns" && (
        <div className="card">
          <h3 className="section-title">Transaction Log ({user.email})</h3>
          <DataTable
            columns={txnColumns}
            data={txns}
            loading={loading}
            emptyMessage="No transaction logs recorded for this account."
          />
        </div>
      )}

      {activeTab === "ledger" && (
        <div className="card">
          <h3 className="section-title">Ledger Logs ({user.email})</h3>
          <DataTable
            columns={ledgerColumns}
            data={ledger}
            loading={loading}
            emptyMessage="No ledger logs recorded for this account."
          />
        </div>
      )}
    </div>
  );
}
