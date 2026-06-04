"use client";

import React, { useState } from "react";

interface ChartDataPoint {
  label: string;
  value: number;
}

interface AreaChartProps {
  data: ChartDataPoint[];
  height?: number;
  prefix?: string;
  suffix?: string;
}

export default function AreaChart({ data, height = 240, prefix = "", suffix = "" }: AreaChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-3)" }}>
        No data available
      </div>
    );
  }

  // Find bounds
  const values = data.map((d) => d.value);
  const maxValue = Math.max(...values, 100); // minimum max value of 100 to prevent division issues
  const minValue = Math.min(...values, 0);

  // SVG parameters
  const paddingX = 40;
  const paddingY = 20;
  const svgWidth = 600;
  const svgHeight = height;

  const chartWidth = svgWidth - paddingX * 2;
  const chartHeight = svgHeight - paddingY * 2;

  // Calculate coordinates
  const points = data.map((d, index) => {
    const x = paddingX + (index / (data.length - 1)) * chartWidth;
    const valueRange = maxValue - minValue;
    const y =
      paddingY +
      chartHeight -
      ((d.value - minValue) / (valueRange || 1)) * chartHeight;
    return { x, y, value: d.value, label: d.label };
  });

  // Construct Area and Line Paths
  let linePath = "";
  let areaPath = "";

  if (points.length > 0) {
    // Generate curved line paths
    linePath = `M ${points[0].x} ${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      const p0 = points[i - 1];
      const p1 = points[i];
      // Control points for bezier curve
      const cpX1 = p0.x + (p1.x - p0.x) / 2;
      const cpY1 = p0.y;
      const cpX2 = p0.x + (p1.x - p0.x) / 2;
      const cpY2 = p1.y;
      linePath += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${p1.x} ${p1.y}`;
    }

    // Generate area path that closes at the bottom
    areaPath = `${linePath} L ${points[points.length - 1].x} ${paddingY + chartHeight} L ${points[0].x} ${paddingY + chartHeight} Z`;
  }

  // Helper to format currency/numbers
  const formatVal = (val: number) => {
    return `${prefix}${val.toLocaleString(undefined, { maximumFractionDigits: 0 })}${suffix}`;
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        width="100%"
        height={svgHeight}
        style={{ overflow: "visible" }}
      >
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--blue)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--blue)" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Horizontal gridlines */}
        {Array.from({ length: 4 }).map((_, i) => {
          const y = paddingY + (i / 3) * chartHeight;
          const val = maxValue - (i / 3) * (maxValue - minValue);
          return (
            <g key={i}>
              <line
                x1={paddingX}
                y1={y}
                x2={svgWidth - paddingX}
                y2={y}
                stroke="var(--border)"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
              <text
                x={paddingX - 8}
                y={y + 4}
                textAnchor="end"
                fontSize={10}
                fill="var(--text-3)"
                fontWeight={500}
              >
                {formatVal(val)}
              </text>
            </g>
          );
        })}

        {/* Shaded Area */}
        {areaPath && (
          <path d={areaPath} fill="url(#chartGradient)" />
        )}

        {/* Main Line */}
        {linePath && (
          <path
            d={linePath}
            fill="none"
            stroke="var(--blue)"
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Axis line */}
        <line
          x1={paddingX}
          y1={paddingY + chartHeight}
          x2={svgWidth - paddingX}
          y2={paddingY + chartHeight}
          stroke="var(--border)"
          strokeWidth={1}
        />

        {/* Labels and interactable dots */}
        {points.map((p, index) => {
          const isHovered = hoveredIndex === index;
          return (
            <g key={index}>
              {/* Vertical dotted line on hover */}
              {isHovered && (
                <line
                  x1={p.x}
                  y1={paddingY}
                  x2={p.x}
                  y2={paddingY + chartHeight}
                  stroke="var(--blue)"
                  strokeDasharray="2 2"
                  strokeWidth={1}
                />
              )}

              {/* Data dot */}
              <circle
                cx={p.x}
                cy={p.y}
                r={isHovered ? 6 : 4}
                fill={isHovered ? "var(--blue)" : "var(--white)"}
                stroke="var(--blue)"
                strokeWidth={isHovered ? 2 : 1.5}
                style={{ cursor: "pointer", transition: "all 0.15s ease" }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              />

              {/* X Axis Label */}
              {index % Math.max(1, Math.floor(points.length / 6)) === 0 && (
                <text
                  x={p.x}
                  y={paddingY + chartHeight + 16}
                  textAnchor="middle"
                  fontSize={10}
                  fill="var(--text-2)"
                  fontWeight={500}
                >
                  {p.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Tooltip Overlay */}
      {hoveredIndex !== null && points[hoveredIndex] && (
        <div
          style={{
            position: "absolute",
            left: `${((points[hoveredIndex].x - paddingX) / chartWidth) * 100}%`,
            top: `${(points[hoveredIndex].y / svgHeight) * 100 - 15}%`,
            transform: "translate(-50%, -100%)",
            background: "var(--text)",
            color: "var(--white)",
            padding: "6px 10px",
            borderRadius: "var(--radius-sm)",
            fontSize: "12px",
            fontWeight: 600,
            pointerEvents: "none",
            boxShadow: "var(--shadow-md)",
            zIndex: 10,
            whiteSpace: "nowrap",
          }}
        >
          <div style={{ fontSize: "10px", color: "var(--text-3)", fontWeight: 400 }}>
            {points[hoveredIndex].label}
          </div>
          <div>{formatVal(points[hoveredIndex].value)}</div>
        </div>
      )}
    </div>
  );
}
