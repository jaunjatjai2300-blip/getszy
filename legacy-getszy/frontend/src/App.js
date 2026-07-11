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
import About from "@/pages/About";
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
import Analytics from "@/pages/admin/Analytics";
import UsersAdmin from "@/pages/admin/UsersAdmin";
import AdminSettings from "@/pages/admin/AdminSettings";
import AdminProjects from "@/pages/admin/Projects";
import AdminSecurity from "@/pages/admin/Security";
import AdminServers from "@/pages/admin/Servers";
import AdminWorkflows from "@/pages/admin/Workflows";
import AdminScheduler from "@/pages/admin/Scheduler";
import AvatarSetup from "@/pages/admin/AvatarSetup";
import AdminCoupons from "@/pages/admin/Coupons";
import AdminInvoices from "@/pages/admin/Invoices";
import AdminReviews from "@/pages/admin/Reviews";
import AdminAffiliates from "@/pages/admin/Affiliates";
import AdminMemberships from "@/pages/admin/Memberships";
import AdminFormBuilder from "@/pages/admin/FormBuilder";
import AdminDashboardBuilder from "@/pages/admin/DashboardBuilder";
import AdminEmailBuilder from "@/pages/admin/EmailBuilder";
import AdminLandingPageBuilder from "@/pages/admin/LandingPageBuilder";
import AdminDBBuilder from "@/pages/admin/DBBuilder";
import AdminAPIBuilder from "@/pages/admin/APIBuilder";
import AdminPromptLibrary from "@/pages/admin/PromptLibrary";
import AdminKnowledgeBase from "@/pages/admin/KnowledgeBase";
import AdminAIMemory from "@/pages/admin/AIMemory";
import AdminAIPlayground from "@/pages/admin/AIPlayground";
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
            <Route path="/about" element={<About />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/support" element={<Support />} />
          </Route>

          <Route path="/admin" element={<AdminLayout />}>
            {/* Dashboard */}
            <Route index element={<AdminDashboard />} />
            <Route path="overview" element={<AdminDashboard />} />
            <Route path="projects" element={<AdminProjects />} />

            {/* Neo AI Chat */}
            <Route path="chat" element={<AdminChatHome />} />
            <Route path="chat/:sessionId" element={<AdminChatHome />} />

            {/* Builders */}
            <Route path="build" element={<AdminBuildStudio />} />
            <Route path="build-web" element={<AdminBuildStudio />} />
            <Route path="build-mobile" element={<AdminBuildStudio />} />
            <Route path="build-api" element={<AdminBuildStudio />} />
            <Route path="build-db" element={<AdminBuildStudio />} />
            <Route path="builder/form" element={<AdminFormBuilder />} />
            <Route path="builder/dashboard" element={<AdminDashboardBuilder />} />
            <Route path="builder/email" element={<AdminEmailBuilder />} />
            <Route path="builder/landing" element={<AdminLandingPageBuilder />} />
            <Route path="builder/db" element={<AdminDBBuilder />} />
            <Route path="builder/api" element={<AdminAPIBuilder />} />

            {/* AI Platform */}
            <Route path="video" element={<AdminVideoStudio />} />
            <Route path="creator" element={<AdminCreatorOS />} />
            <Route path="avatar" element={<AdminVideoStudio />} />
            <Route path="workforce" element={<AdminWorkforce />} />
            <Route path="ai-models" element={<AdminAiOps />} />
            <Route path="voice" element={<AdminCreatorOS />} />
            <Route path="ai/prompts" element={<AdminPromptLibrary />} />
            <Route path="ai/knowledge" element={<AdminKnowledgeBase />} />
            <Route path="ai/memory" element={<AdminAIMemory />} />
            <Route path="ai/playground" element={<AdminAIPlayground />} />

            {/* Commerce */}
            <Route path="products" element={<AdminProducts />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="customers" element={<AdminCustomers />} />
            <Route path="suppliers" element={<AdminSuppliers />} />
            <Route path="sourcing" element={<AdminSourcing />} />
            <Route path="courses" element={<AdminCourses />} />
            <Route path="publishing" element={<AdminPublishing />} />
            <Route path="coupons" element={<AdminCoupons />} />
            <Route path="invoices" element={<AdminInvoices />} />
            <Route path="reviews" element={<AdminReviews />} />
            <Route path="affiliates" element={<AdminAffiliates />} />
            <Route path="memberships" element={<AdminMemberships />} />

            {/* Users */}
            <Route path="users" element={<UsersAdmin />} />
            <Route path="users/credits" element={<UsersAdmin />} />
            <Route path="users/subs" element={<UsersAdmin />} />
            <Route path="users/sessions" element={<UsersAdmin />} />

            {/* Analytics */}
            <Route path="analytics" element={<Analytics />} />
            <Route path="analytics/revenue" element={<Analytics />} />
            <Route path="analytics/ai" element={<Analytics />} />
            <Route path="analytics/content" element={<Analytics />} />

            {/* Automation */}
            <Route path="skills" element={<AdminSkills />} />
            <Route path="stacks" element={<AdminStacks />} />
            <Route path="workflows" element={<AdminStacks />} />
            <Route path="scheduler" element={<AdminStacks />} />
            <Route path="webhooks" element={<AdminStacks />} />

            {/* Deploy */}
            <Route path="deploy" element={<AdminDeploy />} />

            {/* Operations */}
            <Route path="ai-ops" element={<AdminAiOps />} />
            <Route path="servers" element={<AdminServers />} />
            <Route path="workflows" element={<AdminWorkflows />} />
            <Route path="scheduler" element={<AdminScheduler />} />
            <Route path="ai-chat" element={<AdminAIChat />} />
            <Route path="avatar-setup" element={<AvatarSetup />} />

            {/* Security */}
            <Route path="security" element={<AdminSecurity />} />
            <Route path="security/logs" element={<AdminSecurity />} />
            <Route path="security/keys" element={<AdminSecurity />} />
            <Route path="security/alerts" element={<AdminSecurity />} />

            {/* Settings */}
            <Route path="settings" element={<AdminSettings />} />
            <Route path="settings/branding" element={<AdminSettings />} />
            <Route path="settings/billing" element={<AdminSettings />} />
            <Route path="settings/integrations" element={<AdminSettings />} />
          </Route>

          {/* Customer Workspace */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<AdminChatHome />} />
            <Route path="chat" element={<AdminChatHome />} />
            <Route path="chat/:sessionId" element={<AdminChatHome />} />
            <Route path="projects" element={<AdminChatHome />} />
            <Route path="video-studio" element={<VideoStudio />} />
          </Route>

          {/* Founder Labs */}
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
