"use client";

import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface Column<T> {
  header: string;
  accessor?: keyof T;
  cell?: (row: T) => React.ReactNode;
  align?: "left" | "center" | "right";
}

interface PaginationMeta {
  page: number;
  total_pages: number;
  total: number;
  page_size: number;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading: boolean;
  meta?: PaginationMeta;
  onPageChange?: (page: number) => void;
  emptyMessage?: string;
}

export default function DataTable<T>({
  columns,
  data,
  loading,
  meta,
  onPageChange,
  emptyMessage = "No records found.",
}: DataTableProps<T>) {
  
  const handlePrevPage = () => {
    if (meta && onPageChange && meta.page > 1) {
      onPageChange(meta.page - 1);
    }
  };

  const handleNextPage = () => {
    if (meta && onPageChange && meta.page < meta.total_pages) {
      onPageChange(meta.page + 1);
    }
  };

  return (
    <div className="table-container">
      <table className="table">
        <thead>
          <tr>
            {columns.map((col, index) => (
              <th
                key={index}
                style={{ textAlign: col.align || "left" }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            // Shimmer skeletons for loading state
            Array.from({ length: 5 }).map((_, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((col, colIndex) => (
                  <td key={colIndex} style={{ textAlign: col.align || "left" }}>
                    <div
                      className="skeleton"
                      style={{
                        height: "18px",
                        width: colIndex === 0 ? "100px" : "60px",
                        borderRadius: "4px",
                      }}
                    />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} style={{ textAlign: "center", color: "var(--text-3)", padding: "var(--space-8)" }}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((col, colIndex) => (
                  <td
                    key={colIndex}
                    style={{ textAlign: col.align || "left" }}
                  >
                    {col.cell ? col.cell(row) : col.accessor ? String(row[col.accessor] ?? "") : ""}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {!loading && meta && meta.total_pages > 1 && (
        <div className="pagination">
          <div className="pagination-info">
            Showing Page <strong>{meta.page}</strong> of <strong>{meta.total_pages}</strong> ({meta.total} total items)
          </div>
          <div className="pagination-buttons">
            <button
              className="btn btn-secondary btn-sm"
              onClick={handlePrevPage}
              disabled={meta.page <= 1}
              style={{ opacity: meta.page <= 1 ? 0.5 : 1, cursor: meta.page <= 1 ? "not-allowed" : "pointer" }}
            >
              <ChevronLeft size={16} /> Prev
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleNextPage}
              disabled={meta.page >= meta.total_pages}
              style={{ opacity: meta.page >= meta.total_pages ? 0.5 : 1, cursor: meta.page >= meta.total_pages ? "not-allowed" : "pointer" }}
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
