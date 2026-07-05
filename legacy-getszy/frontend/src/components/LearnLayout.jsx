import { Outlet } from "react-router-dom";

export default function LearnLayout() {
  return (
    <div className="min-h-screen" style={{ background: "var(--gs-bg)" }}>
      <Outlet />
    </div>
  );
}
