"use client";

import React, { useState, useEffect } from "react";
import { api } from "../../lib/api";
import Modal from "../../components/Modal";
import { RefreshCw, Percent, Edit2, TrendingUp, TrendingDown, Clock, AlertTriangle } from "lucide-react";

interface RateConfigItem {
  asset_code: string;
  asset_name: string;
  buy_markup_percent: number;
  sell_markup_percent: number;
  fallback_market_rate: number;
  last_market_rate: number | null;
  last_synced_at: string | null;
}

export default function RatesPage() {
  const [rates, setRates] = useState<RateConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal state
  const [selectedAsset, setSelectedAsset] = useState<RateConfigItem | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [buyMarkup, setBuyMarkup] = useState("");
  const [sellMarkup, setSellMarkup] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchRates = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<RateConfigItem[]>("/admin/rates");
      setRates(res || []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load rate configurations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRates();
  }, []);

  const handleEditClick = (rate: RateConfigItem) => {
    setSelectedAsset(rate);
    setBuyMarkup(String(rate.buy_markup_percent));
    setSellMarkup(String(rate.sell_markup_percent));
    setIsEditOpen(true);
  };

  const handleUpdateRates = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAsset) return;
    
    const buyVal = parseFloat(buyMarkup);
    const sellVal = parseFloat(sellMarkup);

    if (isNaN(buyVal) || isNaN(sellVal)) {
      alert("Please enter valid decimal numbers for markup values.");
      return;
    }

    setSubmitting(true);
    try {
      await api.patch(`/admin/rates/${selectedAsset.asset_code}`, {
        buy_markup_percent: buyVal,
        sell_markup_percent: sellVal,
      });
      setIsEditOpen(false);
      setSelectedAsset(null);
      fetchRates();
    } catch (err: any) {
      alert(err.message || "Failed to update rates markup.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Markup Rate Configurations</h1>
          <p style={{ color: "var(--text-2)", marginTop: "2px" }}>Manage exchange markup margins for buying and selling cryptocurrency assets.</p>
        </div>

        <button
          onClick={fetchRates}
          className="btn btn-secondary"
          disabled={loading}
        >
          <RefreshCw size={16} style={{ animation: loading ? "spin 0.6s linear infinite" : "none" }} />
          Sync Rates
        </button>
      </div>

      {error && (
        <div style={{ background: "var(--red-light)", color: "var(--red-text)", padding: "var(--space-4)", borderRadius: "var(--radius-lg)", marginBottom: "var(--space-6)" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid-cols-3">
          {Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx} className="skeleton" style={{ height: "240px", borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      ) : rates.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12)" }}>
          <Percent size={48} style={{ color: "var(--text-3)", marginBottom: "var(--space-4)" }} />
          <h3 style={{ color: "var(--text-2)" }}>No Assets Configured</h3>
          <p style={{ color: "var(--text-3)", marginTop: "var(--space-2)" }}>Configure assets in backend to edit markups.</p>
        </div>
      ) : (
        <div className="grid-cols-3">
          {rates.map((rate) => {
            const hasFeed = rate.last_market_rate !== null;
            const marketRate = rate.last_market_rate || rate.fallback_market_rate;
            
            // Calculate final customer rates
            const customerBuyRate = marketRate * (1 + rate.buy_markup_percent / 100);
            const customerSellRate = marketRate * (1 - rate.sell_markup_percent / 100);

            return (
              <div key={rate.asset_code} className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", height: "100%", padding: "var(--space-6)", marginBottom: 0 }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "var(--space-3)", marginBottom: "var(--space-4)" }}>
                    <div>
                      <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text)" }}>{rate.asset_name}</h3>
                      <span style={{ fontSize: "11px", fontWeight: 700, background: "var(--blue-light)", color: "var(--blue)", padding: "2px 6px", borderRadius: "var(--radius-sm)", textTransform: "uppercase" }}>
                        {rate.asset_code}
                      </span>
                    </div>
                    <Percent size={20} style={{ color: "var(--text-3)" }} />
                  </div>

                  {/* Markup Values */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "var(--space-4)" }}>
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "10px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-2)", fontWeight: 600, display: "flex", alignItems: "center", gap: "2px" }}>
                        <TrendingUp size={12} style={{ color: "var(--green-text)" }} /> BUY MARKUP
                      </div>
                      <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px" }}>
                        {rate.buy_markup_percent}%
                      </div>
                    </div>
                    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "10px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-2)", fontWeight: 600, display: "flex", alignItems: "center", gap: "2px" }}>
                        <TrendingDown size={12} style={{ color: "var(--red-text)" }} /> SELL MARKUP
                      </div>
                      <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px" }}>
                        {rate.sell_markup_percent}%
                      </div>
                    </div>
                  </div>

                  {/* Calculations */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", fontSize: "13px", marginBottom: "var(--space-4)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-2)" }}>Market Index Rate:</span>
                      <span style={{ fontWeight: 600 }}>₦{Number(marketRate).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-2)" }}>Customer Buy Price:</span>
                      <span style={{ fontWeight: 700, color: "var(--green-text)" }}>₦{Number(customerBuyRate).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--text-2)" }}>Customer Sell Price:</span>
                      <span style={{ fontWeight: 700, color: "var(--blue)" }}>₦{Number(customerSellRate).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                </div>

                <div style={{ borderTop: "1px solid var(--border)", paddingTop: "var(--space-4)", marginTop: "var(--space-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-2)", fontSize: "11px", marginBottom: "var(--space-4)" }}>
                    <Clock size={12} />
                    <span>
                      {rate.last_synced_at ? (
                        `Synced ${new Date(rate.last_synced_at).toLocaleTimeString()}`
                      ) : (
                        <span style={{ color: "var(--amber-text)", display: "flex", alignItems: "center", gap: "2px" }}>
                          <AlertTriangle size={12} /> Using Fallback Rate
                        </span>
                      )}
                    </span>
                  </div>

                  <button
                    onClick={() => handleEditClick(rate)}
                    className="btn btn-secondary"
                    style={{ width: "100%", display: "flex", gap: "6px" }}
                  >
                    <Edit2 size={14} /> Edit Markup Percent
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* EDIT CONFIG MODAL */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setSelectedAsset(null);
        }}
        title={`Edit Markups — ${selectedAsset?.asset_name} (${selectedAsset?.asset_code})`}
      >
        {selectedAsset && (
          <form onSubmit={handleUpdateRates}>
            <p style={{ fontSize: "13px", color: "var(--text-2)", marginBottom: "var(--space-4)" }}>
              Define the percentage markup relative to the market index rate. Buy markups are added to user cost; sell markups are subtracted from user payout.
            </p>

            <div className="form-group">
              <label className="form-label">Buy Markup Percentage (%)</label>
              <div style={{ position: "relative" }}>
                <Percent size={14} style={{ position: "absolute", right: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
                <input
                  type="number"
                  step="0.01"
                  className="input"
                  value={buyMarkup}
                  onChange={(e) => setBuyMarkup(e.target.value)}
                  placeholder="e.g. 1.50"
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "var(--space-6)" }}>
              <label className="form-label">Sell Markup Percentage (%)</label>
              <div style={{ position: "relative" }}>
                <Percent size={14} style={{ position: "absolute", right: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
                <input
                  type="number"
                  step="0.01"
                  className="input"
                  value={sellMarkup}
                  onChange={(e) => setSellMarkup(e.target.value)}
                  placeholder="e.g. 1.25"
                  required
                />
              </div>
            </div>

            <div className="modal-footer" style={{ padding: 0 }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setIsEditOpen(false);
                  setSelectedAsset(null);
                }}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting}
              >
                {submitting ? "Updating..." : "Save Configuration"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
