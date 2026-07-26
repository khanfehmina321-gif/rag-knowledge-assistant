"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// Formats large numbers in Indian style (lakh/crore) for axis labels
function formatCompactINR(value) {
  if (value >= 1e7) return `₹${(value / 1e7).toFixed(1)}Cr`;
  if (value >= 1e5) return `₹${(value / 1e5).toFixed(1)}L`;
  return `₹${value}`;
}

export default function BarChartDisplay({ chartData }) {
  if (!chartData || !chartData.labels || !chartData.values) return null;

  // Recharts wants an array of objects, not two parallel arrays
  const data = chartData.labels.map((label, idx) => ({
    name: label,
    value: chartData.values[idx],
  }));

  const isLine = chartData.type === "line";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mt-3">
      <h3 className="text-xs uppercase tracking-wide text-gray-500 mb-4">
        {chartData.title || "Chart"}
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        {isLine ? (
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
            <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={formatCompactINR} />
            <Tooltip
              contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151" }}
              labelStyle={{ color: "#e5e7eb" }}
              formatter={(value) => [formatCompactINR(value), "Amount"]}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: "#3b82f6", r: 3 }}
            />
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
            <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={formatCompactINR} />
            <Tooltip
              contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151" }}
              labelStyle={{ color: "#e5e7eb" }}
              formatter={(value) => [formatCompactINR(value), "Amount"]}
            />
            <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}