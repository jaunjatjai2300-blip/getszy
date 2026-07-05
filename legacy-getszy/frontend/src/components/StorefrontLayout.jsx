import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Footer } from "./Footer";

export default function StorefrontLayout() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--gs-bg)" }}>
      <Header />
      <main id="main-content" className="flex-1" tabIndex={-1}>
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
