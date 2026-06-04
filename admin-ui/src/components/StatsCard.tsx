import React from "react";
import { LucideIcon } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: string | number;
  change?: {
    value: string | number;
    isPositive: boolean;
    label?: string;
  };
  icon?: LucideIcon;
}

export default function StatsCard({ label, value, change, icon: Icon }: StatsCardProps) {
  return (
    <div className="stats-card">
      <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-1)" }}>
        <span className="label">{label}</span>
        {Icon && <Icon size={18} style={{ color: "var(--text-2)" }} />}
      </div>
      <div className="value">{value}</div>
      {change && (
        <div className={`change ${change.isPositive ? "positive" : "negative"}`}>
          <span>
            {change.isPositive ? "+" : ""}
            {change.value}
          </span>
          {change.label && (
            <span style={{ color: "var(--text-3)", fontWeight: 400, marginLeft: "4px" }}>
              {change.label}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
