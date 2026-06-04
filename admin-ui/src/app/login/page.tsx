"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../lib/auth";
import { useSearchParams } from "next/navigation";
import { TrendingUp, Lock, Mail, AlertCircle, Settings, Check, RefreshCw } from "lucide-react";
import { getApiUrl, setCustomApiUrl } from "../../lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const searchParams = useSearchParams();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Custom API URL config
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    setApiUrl(getApiUrl());
    if (searchParams.get("expired")) {
      setError("Your admin session has expired. Please log in again.");
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }
    
    setError(null);
    setLoading(true);
    
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Failed to log in. Please check your credentials.");
      setLoading(false);
    }
  };

  const handleSaveApiUrl = () => {
    if (!apiUrl.trim()) return;
    setCustomApiUrl(apiUrl.trim());
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      background: "var(--surface)",
      padding: "var(--space-6)"
    }}>
      <div className="card" style={{ 
        maxWidth: "420px", 
        width: "100%", 
        padding: "var(--space-8)",
        pointerEvents: loading ? "none" : "auto",
        opacity: loading ? 0.8 : 1,
        transition: "opacity 0.2s ease"
      }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: "var(--space-8)" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "48px",
            height: "48px",
            borderRadius: "var(--radius-lg)",
            background: "var(--blue-light)",
            color: "var(--blue)",
            marginBottom: "var(--space-3)"
          }}>
            <TrendingUp size={28} />
          </div>
          <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--text)" }}>
            CheeseBall Admin
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-2)", marginTop: "2px" }}>
            Sign in to access control panel
          </p>
        </div>

        {error && (
          <div style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            background: "var(--red-light)",
            color: "var(--red-text)",
            padding: "12px",
            borderRadius: "var(--radius-md)",
            fontSize: "13px",
            fontWeight: 500,
            marginBottom: "var(--space-4)"
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div style={{ position: "relative" }}>
              <Mail size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
              <input
                type="email"
                className="input"
                placeholder="admin@cheeseballapp.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ paddingLeft: "40px" }}
                disabled={loading}
                required
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: "var(--space-6)" }}>
            <label className="form-label">Password</label>
            <div style={{ position: "relative" }}>
              <Lock size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }} />
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: "40px" }}
                disabled={loading}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", height: "42px", fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
            disabled={loading}
          >
            {loading ? (
              <>
                <RefreshCw size={16} style={{ animation: "spin 0.6s linear infinite" }} />
                Authenticating...
              </>
            ) : (
              "Sign In to Dashboard"
            )}
          </button>
        </form>

        <div style={{ marginTop: "var(--space-6)", borderTop: "1px solid var(--border)", paddingTop: "var(--space-4)" }}>
          <button
            onClick={() => setShowSettings(!showSettings)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "none",
              border: "none",
              color: "var(--text-2)",
              fontSize: "12px",
              fontWeight: 500,
              cursor: "pointer",
              margin: "0 auto"
            }}
          >
            <Settings size={14} />
            {showSettings ? "Hide API Settings" : "Configure Backend URL"}
          </button>

          {showSettings && (
            <div style={{
              marginTop: "var(--space-3)",
              background: "var(--surface)",
              padding: "12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)"
            }}>
              <label className="form-label" style={{ fontSize: "10px" }}>Backend Host URL</label>
              <div style={{ display: "flex", gap: "6px" }}>
                <input
                  type="text"
                  className="input"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  style={{ fontSize: "12px", padding: "6px 10px" }}
                />
                <button
                  onClick={handleSaveApiUrl}
                  className="btn btn-primary"
                  style={{ padding: "6px 12px", fontSize: "12px" }}
                >
                  {saveSuccess ? <Check size={14} /> : "Save"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
