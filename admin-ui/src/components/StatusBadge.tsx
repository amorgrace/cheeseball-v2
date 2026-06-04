import React from "react";

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase().replace(/_/g, " ");

  let badgeClass = "badge-neutral";
  
  if (
    normalized === "completed" ||
    normalized === "verified" ||
    normalized === "active" ||
    normalized === "success" ||
    normalized === "approve"
  ) {
    badgeClass = "badge-success";
  } else if (
    normalized === "failed" ||
    normalized === "rejected" ||
    normalized === "inactive" ||
    normalized === "error" ||
    normalized === "reject"
  ) {
    badgeClass = "badge-error";
  } else if (
    normalized === "pending" ||
    normalized === "submitted" ||
    normalized === "pending payment" ||
    normalized === "pending review" ||
    normalized === "processing"
  ) {
    badgeClass = "badge-warning";
  } else if (
    normalized === "paid" ||
    normalized === "info" ||
    normalized === "staff"
  ) {
    badgeClass = "badge-info";
  }

  // Capitalize first letter of each word
  const label = normalized
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  return <span className={`badge ${badgeClass}`}>{label}</span>;
}
