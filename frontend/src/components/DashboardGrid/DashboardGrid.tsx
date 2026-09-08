"use client";

// DashboardGrid: layout primitive with explicit left/right slots — { left: ReactNode; right: ReactNode }
type DashboardGridProps = {
  left: React.ReactNode;
  right: React.ReactNode;
};

export default function DashboardGrid({ left, right }: DashboardGridProps) {
  return (
    <div style={{ width: "100%" }} className="dashboard-grid">
      {left}
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", height: "100%" }}>
        {right}
      </div>
    </div>
  );
}
