import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/lib/auth";
import Home from "@/pages/Home";
import Shop from "@/pages/Shop";
import ProductDetail from "@/pages/ProductDetail";
import Cart from "@/pages/Cart";
import Checkout from "@/pages/Checkout";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Account from "@/pages/Account";
import Pricing from "@/pages/Pricing";
import Terms from "@/pages/Terms";
import Privacy from "@/pages/Privacy";
import Support from "@/pages/Support";
import AdminLayout from "@/components/AdminLayout";
import AdminDashboard from "@/pages/admin/Dashboard";
import AdminProducts from "@/pages/admin/Products";
import AdminOrders from "@/pages/admin/Orders";
import AdminSuppliers from "@/pages/admin/Suppliers";
import AdminCustomers from "@/pages/admin/Customers";
import AdminCourses from "@/pages/admin/Courses";
import AdminAIChat from "@/pages/admin/AIChat";
import AdminAiOps from "@/pages/admin/AiOps";
import AdminSourcing from "@/pages/admin/Sourcing";
import AdminDeploy from "@/pages/admin/Deploy";
import AdminSkills from "@/pages/admin/Skills";
import AdminStacks from "@/pages/admin/Stacks";
import AdminCreatorOS from "@/pages/admin/CreatorOS";
import AdminVideoStudio from "@/pages/admin/VideoStudio";
import AdminPublishing from "@/pages/admin/Publishing";
import AdminWorkforce from "@/pages/admin/Workforce";
import AdminBuildStudio from "@/pages/admin/BuildStudio";
import AdminChatHome from "@/pages/admin/ChatHome";
import VideoStudio from "@/pages/dashboard/VideoStudio";
import DashboardLayout from "@/components/DashboardLayout";
import LabsHome from "@/pages/labs/LabsHome";
import CommandPalette from "@/components/ux/CommandPalette";
import OnboardingTour from "@/components/onboarding/OnboardingTour";
import CookieConsent from "@/components/legal/CookieConsent";
import StorefrontLayout from "@/components/StorefrontLayout";
import NotFound from "@/pages/NotFound";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function App() {
  return (
    <ErrorBoundary>
    <AuthProvider>
      <BrowserRouter>
        <a href="#main-content" className="skip-to-content" data-testid="skip-to-content">Skip to main content</a>
        <Routes>
          <Route element={<StorefrontLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/shop" element={<Shop />} />
            <Route path="/category/:slug" element={<Shop />} />
            <Route path="/product/:id" element={<ProductDetail />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/account" element={<Account />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/support" element={<Support />} />
          </Route>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="chat" element={<AdminChatHome />} />
            <Route path="chat/:sessionId" element={<AdminChatHome />} />
            <Route path="overview" element={<AdminDashboard />} />
            <Route path="products" element={<AdminProducts />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="suppliers" element={<AdminSuppliers />} />
            <Route path="customers" element={<AdminCustomers />} />
            <Route path="courses" element={<AdminCourses />} />
            <Route path="sourcing" element={<AdminSourcing />} />
            <Route path="deploy" element={<AdminDeploy />} />
            <Route path="skills" element={<AdminSkills />} />
            <Route path="stacks" element={<AdminStacks />} />
            <Route path="creator" element={<AdminCreatorOS />} />
            <Route path="video" element={<AdminVideoStudio />} />
            <Route path="publishing" element={<AdminPublishing />} />
            <Route path="workforce" element={<AdminWorkforce />} />
            <Route path="build" element={<AdminBuildStudio />} />
            <Route path="ai-ops" element={<AdminAiOps />} />
            <Route path="ai-chat" element={<AdminAIChat />} />
          </Route>

          {/* Customer Workspace — Neo is the front door */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<AdminChatHome />} />
            <Route path="chat" element={<AdminChatHome />} />
            <Route path="chat/:sessionId" element={<AdminChatHome />} />
            <Route path="projects" element={<AdminChatHome />} />
            <Route path="video-studio" element={<VideoStudio />} />
          </Route>

          {/* Founder Labs — internal-only */}
          <Route path="/labs" element={<DashboardLayout />}>
            <Route index element={<LabsHome />} />
            <Route path="chat/:sessionId" element={<AdminChatHome />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
        <CommandPalette />
        <OnboardingTour />
        <CookieConsent />
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
    </ErrorBoundary>
  );
}
