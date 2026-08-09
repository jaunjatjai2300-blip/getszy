import { lazy, Suspense } from "react";
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
import VideoStudio from "@/pages/dashboard/VideoStudio";
import DashboardLayout from "@/components/DashboardLayout";
import LabsHome from "@/pages/labs/LabsHome";
import CommandPalette from "@/components/ux/CommandPalette";
import OnboardingTour from "@/components/onboarding/OnboardingTour";
import CookieConsent from "@/components/legal/CookieConsent";
import StorefrontLayout from "@/components/StorefrontLayout";
import NotFound from "@/pages/NotFound";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const AdminDashboard = lazy(() => import("@/pages/admin/Dashboard"));
const AdminProducts = lazy(() => import("@/pages/admin/Products"));
const AdminOrders = lazy(() => import("@/pages/admin/Orders"));
const AdminSuppliers = lazy(() => import("@/pages/admin/Suppliers"));
const AdminCustomers = lazy(() => import("@/pages/admin/Customers"));
const AdminCourses = lazy(() => import("@/pages/admin/Courses"));
const AdminAIChat = lazy(() => import("@/pages/admin/AIChat"));
const AdminAiOps = lazy(() => import("@/pages/admin/AiOps"));
const AdminSourcing = lazy(() => import("@/pages/admin/Sourcing"));
const AdminDeploy = lazy(() => import("@/pages/admin/Deploy"));
const AdminSkills = lazy(() => import("@/pages/admin/Skills"));
const AdminStacks = lazy(() => import("@/pages/admin/Stacks"));
const AdminCreatorOS = lazy(() => import("@/pages/admin/CreatorOS"));
const AdminVideoStudio = lazy(() => import("@/pages/admin/VideoStudio"));
const AdminPublishing = lazy(() => import("@/pages/admin/Publishing"));
const AdminWorkforce = lazy(() => import("@/pages/admin/Workforce"));
const AdminBuildStudio = lazy(() => import("@/pages/admin/BuildStudio"));
const AdminChatHome = lazy(() => import("@/pages/admin/ChatHome"));
const Analytics = lazy(() => import("@/pages/admin/Analytics"));
const UsersAdmin = lazy(() => import("@/pages/admin/UsersAdmin"));
const AdminSettings = lazy(() => import("@/pages/admin/AdminSettings"));
const AdminProjects = lazy(() => import("@/pages/admin/Projects"));
const AdminSecurity = lazy(() => import("@/pages/admin/Security"));
const AdminServers = lazy(() => import("@/pages/admin/Servers"));
const AdminWorkflows = lazy(() => import("@/pages/admin/Workflows"));
const AdminScheduler = lazy(() => import("@/pages/admin/Scheduler"));
const AvatarSetup = lazy(() => import("@/pages/admin/AvatarSetup"));
const AdminCoupons = lazy(() => import("@/pages/admin/Coupons"));
const AdminInvoices = lazy(() => import("@/pages/admin/Invoices"));
const AdminReviews = lazy(() => import("@/pages/admin/Reviews"));
const AdminAffiliates = lazy(() => import("@/pages/admin/Affiliates"));
const AdminMemberships = lazy(() => import("@/pages/admin/Memberships"));
const AdminFormBuilder = lazy(() => import("@/pages/admin/FormBuilder"));
const AdminDashboardBuilder = lazy(() => import("@/pages/admin/DashboardBuilder"));
const AdminEmailBuilder = lazy(() => import("@/pages/admin/EmailBuilder"));
const AdminLandingPageBuilder = lazy(() => import("@/pages/admin/LandingPageBuilder"));
const AdminDBBuilder = lazy(() => import("@/pages/admin/DBBuilder"));
const AdminAPIBuilder = lazy(() => import("@/pages/admin/APIBuilder"));
const AdminVideoBuilder = lazy(() => import("@/pages/admin/VideoBuilder"));
const AdminChatbotBuilder = lazy(() => import("@/pages/admin/ChatbotBuilder"));
const AdminAutomationBuilder = lazy(() => import("@/pages/admin/AutomationBuilder"));
const AdminReportBuilder = lazy(() => import("@/pages/admin/ReportBuilder"));
const AdminSiteBuilder = lazy(() => import("@/pages/admin/SiteBuilder"));
const AdminWorkflowBuilder = lazy(() => import("@/pages/admin/WorkflowBuilder"));
const AdminRefunds = lazy(() => import("@/pages/admin/Refunds"));
const AdminGST = lazy(() => import("@/pages/admin/GST"));
const FounderCommand = lazy(() => import("@/pages/admin/FounderCommand"));
const EnterpriseSecurity = lazy(() => import("@/pages/admin/EnterpriseSecurity"));
const DeployPlatform = lazy(() => import("@/pages/admin/DeployPlatform"));
const SaaSBuilder = lazy(() => import("@/pages/admin/SaaSBuilder"));
const WooSync = lazy(() => import("@/pages/admin/WooSync"));
const MobileBuilder = lazy(() => import("@/pages/admin/MobileBuilder"));
const BusinessBuilders = lazy(() => import("@/pages/admin/BusinessBuilders"));
const AdvancedAnalytics = lazy(() => import("@/pages/admin/AdvancedAnalytics"));
const GrowthEngine = lazy(() => import("@/pages/admin/GrowthEngine"));
const Marketplace = lazy(() => import("@/pages/admin/Marketplace"));
const LearningPlatform = lazy(() => import("@/pages/admin/LearningPlatform"));
const OperationsCenter = lazy(() => import("@/pages/admin/OperationsCenter"));
const AdminPromptLibrary = lazy(() => import("@/pages/admin/PromptLibrary"));
const AdminKnowledgeBase = lazy(() => import("@/pages/admin/KnowledgeBase"));
const AdminAIMemory = lazy(() => import("@/pages/admin/AIMemory"));
const AdminAIPlayground = lazy(() => import("@/pages/admin/AIPlayground"));
const CostTracking = lazy(() => import("@/pages/admin/CostTracking"));
const QuizCerts = lazy(() => import("@/pages/admin/QuizCerts"));
const VoiceGen = lazy(() => import("@/pages/admin/VoiceGen"));
const ImageGen = lazy(() => import("@/pages/admin/ImageGen"));
const Releases = lazy(() => import("@/pages/admin/Releases"));

function AdminFallback() {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 border-2 border-[var(--gs-teal)] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-[var(--gs-muted)]">Loading...</span>
      </div>
    </div>
  );
}

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
            <Route index element={<Suspense fallback={<AdminFallback />}><AdminDashboard /></Suspense>} />
            <Route path="overview" element={<Suspense fallback={<AdminFallback />}><AdminDashboard /></Suspense>} />
            <Route path="projects" element={<Suspense fallback={<AdminFallback />}><AdminProjects /></Suspense>} />

            <Route path="chat" element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />
            <Route path="chat/:sessionId" element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />

            <Route path="build" element={<Suspense fallback={<AdminFallback />}><AdminBuildStudio /></Suspense>} />
            <Route path="build-web" element={<Suspense fallback={<AdminFallback />}><AdminBuildStudio /></Suspense>} />
            <Route path="build-mobile" element={<Suspense fallback={<AdminFallback />}><AdminBuildStudio /></Suspense>} />
            <Route path="build-api" element={<Suspense fallback={<AdminFallback />}><AdminBuildStudio /></Suspense>} />
            <Route path="build-db" element={<Suspense fallback={<AdminFallback />}><AdminBuildStudio /></Suspense>} />
            <Route path="builder/form" element={<Suspense fallback={<AdminFallback />}><AdminFormBuilder /></Suspense>} />
            <Route path="builder/dashboard" element={<Suspense fallback={<AdminFallback />}><AdminDashboardBuilder /></Suspense>} />
            <Route path="builder/email" element={<Suspense fallback={<AdminFallback />}><AdminEmailBuilder /></Suspense>} />
            <Route path="builder/landing" element={<Suspense fallback={<AdminFallback />}><AdminLandingPageBuilder /></Suspense>} />
            <Route path="builder/db" element={<Suspense fallback={<AdminFallback />}><AdminDBBuilder /></Suspense>} />
            <Route path="builder/api" element={<Suspense fallback={<AdminFallback />}><AdminAPIBuilder /></Suspense>} />
            <Route path="builder/video" element={<Suspense fallback={<AdminFallback />}><AdminVideoBuilder /></Suspense>} />
            <Route path="builder/chatbot" element={<Suspense fallback={<AdminFallback />}><AdminChatbotBuilder /></Suspense>} />
            <Route path="builder/automation" element={<Suspense fallback={<AdminFallback />}><AdminAutomationBuilder /></Suspense>} />
            <Route path="builder/report" element={<Suspense fallback={<AdminFallback />}><AdminReportBuilder /></Suspense>} />
            <Route path="builder/site" element={<Suspense fallback={<AdminFallback />}><AdminSiteBuilder /></Suspense>} />
            <Route path="builder/workflow" element={<Suspense fallback={<AdminFallback />}><AdminWorkflowBuilder /></Suspense>} />

            <Route path="video" element={<Suspense fallback={<AdminFallback />}><AdminVideoStudio /></Suspense>} />
            <Route path="creator" element={<Suspense fallback={<AdminFallback />}><AdminCreatorOS /></Suspense>} />
            <Route path="avatar" element={<Suspense fallback={<AdminFallback />}><AvatarSetup /></Suspense>} />
            <Route path="workforce" element={<Suspense fallback={<AdminFallback />}><AdminWorkforce /></Suspense>} />
            <Route path="ai-models" element={<Suspense fallback={<AdminFallback />}><AdminAiOps /></Suspense>} />
            <Route path="voice" element={<Suspense fallback={<AdminFallback />}><VoiceGen /></Suspense>} />
            <Route path="ai/prompts" element={<Suspense fallback={<AdminFallback />}><AdminPromptLibrary /></Suspense>} />
            <Route path="ai/knowledge" element={<Suspense fallback={<AdminFallback />}><AdminKnowledgeBase /></Suspense>} />
            <Route path="ai/memory" element={<Suspense fallback={<AdminFallback />}><AdminAIMemory /></Suspense>} />
            <Route path="ai/playground" element={<Suspense fallback={<AdminFallback />}><AdminAIPlayground /></Suspense>} />

            <Route path="products" element={<Suspense fallback={<AdminFallback />}><AdminProducts /></Suspense>} />
            <Route path="orders" element={<Suspense fallback={<AdminFallback />}><AdminOrders /></Suspense>} />
            <Route path="customers" element={<Suspense fallback={<AdminFallback />}><AdminCustomers /></Suspense>} />
            <Route path="suppliers" element={<Suspense fallback={<AdminFallback />}><AdminSuppliers /></Suspense>} />
            <Route path="sourcing" element={<Suspense fallback={<AdminFallback />}><AdminSourcing /></Suspense>} />
            <Route path="courses" element={<Suspense fallback={<AdminFallback />}><AdminCourses /></Suspense>} />
            <Route path="publishing" element={<Suspense fallback={<AdminFallback />}><AdminPublishing /></Suspense>} />
            <Route path="coupons" element={<Suspense fallback={<AdminFallback />}><AdminCoupons /></Suspense>} />
            <Route path="invoices" element={<Suspense fallback={<AdminFallback />}><AdminInvoices /></Suspense>} />
            <Route path="reviews" element={<Suspense fallback={<AdminFallback />}><AdminReviews /></Suspense>} />
            <Route path="affiliates" element={<Suspense fallback={<AdminFallback />}><AdminAffiliates /></Suspense>} />
            <Route path="memberships" element={<Suspense fallback={<AdminFallback />}><AdminMemberships /></Suspense>} />
            <Route path="refunds" element={<Suspense fallback={<AdminFallback />}><AdminRefunds /></Suspense>} />
            <Route path="gst" element={<Suspense fallback={<AdminFallback />}><AdminGST /></Suspense>} />

            <Route path="users" element={<Suspense fallback={<AdminFallback />}><UsersAdmin /></Suspense>} />
            <Route path="users/credits" element={<Suspense fallback={<AdminFallback />}><UsersAdmin /></Suspense>} />
            <Route path="users/subs" element={<Suspense fallback={<AdminFallback />}><UsersAdmin /></Suspense>} />
            <Route path="users/sessions" element={<Suspense fallback={<AdminFallback />}><UsersAdmin /></Suspense>} />

            <Route path="analytics" element={<Suspense fallback={<AdminFallback />}><Analytics /></Suspense>} />
            <Route path="analytics/revenue" element={<Suspense fallback={<AdminFallback />}><Analytics /></Suspense>} />
            <Route path="analytics/ai" element={<Suspense fallback={<AdminFallback />}><Analytics /></Suspense>} />
            <Route path="analytics/content" element={<Suspense fallback={<AdminFallback />}><Analytics /></Suspense>} />

            <Route path="skills" element={<Suspense fallback={<AdminFallback />}><AdminSkills /></Suspense>} />
            <Route path="stacks" element={<Suspense fallback={<AdminFallback />}><AdminStacks /></Suspense>} />
            <Route path="workflows" element={<Suspense fallback={<AdminFallback />}><AdminWorkflows /></Suspense>} />
            <Route path="scheduler" element={<Suspense fallback={<AdminFallback />}><AdminScheduler /></Suspense>} />
            <Route path="webhooks" element={<Suspense fallback={<AdminFallback />}><AdminStacks /></Suspense>} />

            <Route path="deploy" element={<Suspense fallback={<AdminFallback />}><AdminDeploy /></Suspense>} />

            <Route path="ai-ops" element={<Suspense fallback={<AdminFallback />}><AdminAiOps /></Suspense>} />
            <Route path="servers" element={<Suspense fallback={<AdminFallback />}><AdminServers /></Suspense>} />
            <Route path="ai-chat" element={<Suspense fallback={<AdminFallback />}><AdminAIChat /></Suspense>} />
            <Route path="avatar-setup" element={<Suspense fallback={<AdminFallback />}><AvatarSetup /></Suspense>} />

            <Route path="security" element={<Suspense fallback={<AdminFallback />}><AdminSecurity /></Suspense>} />
            <Route path="security/logs" element={<Suspense fallback={<AdminFallback />}><AdminSecurity /></Suspense>} />
            <Route path="security/keys" element={<Suspense fallback={<AdminFallback />}><AdminSecurity /></Suspense>} />
            <Route path="security/alerts" element={<Suspense fallback={<AdminFallback />}><AdminSecurity /></Suspense>} />

            <Route path="founder" element={<Suspense fallback={<AdminFallback />}><FounderCommand /></Suspense>} />
            <Route path="enterprise-security" element={<Suspense fallback={<AdminFallback />}><EnterpriseSecurity /></Suspense>} />
            <Route path="deploy-platform" element={<Suspense fallback={<AdminFallback />}><DeployPlatform /></Suspense>} />
            <Route path="saas-builder" element={<Suspense fallback={<AdminFallback />}><SaaSBuilder /></Suspense>} />
            <Route path="woo-sync" element={<Suspense fallback={<AdminFallback />}><WooSync /></Suspense>} />
            <Route path="api-builder" element={<Suspense fallback={<AdminFallback />}><AdminAPIBuilder /></Suspense>} />
            <Route path="mobile-builder" element={<Suspense fallback={<AdminFallback />}><MobileBuilder /></Suspense>} />
            <Route path="business-builders" element={<Suspense fallback={<AdminFallback />}><BusinessBuilders /></Suspense>} />
            <Route path="analytics-advanced" element={<Suspense fallback={<AdminFallback />}><AdvancedAnalytics /></Suspense>} />
            <Route path="growth" element={<Suspense fallback={<AdminFallback />}><GrowthEngine /></Suspense>} />
            <Route path="marketplace" element={<Suspense fallback={<AdminFallback />}><Marketplace /></Suspense>} />
            <Route path="learning-platform" element={<Suspense fallback={<AdminFallback />}><LearningPlatform /></Suspense>} />
            <Route path="ops-center" element={<Suspense fallback={<AdminFallback />}><OperationsCenter /></Suspense>} />
            <Route path="cost-tracking" element={<Suspense fallback={<AdminFallback />}><CostTracking /></Suspense>} />
            <Route path="quiz-certs" element={<Suspense fallback={<AdminFallback />}><QuizCerts /></Suspense>} />
            <Route path="image-gen" element={<Suspense fallback={<AdminFallback />}><ImageGen /></Suspense>} />
            <Route path="releases" element={<Suspense fallback={<AdminFallback />}><Releases /></Suspense>} />

            <Route path="settings" element={<Suspense fallback={<AdminFallback />}><AdminSettings /></Suspense>} />
            <Route path="settings/branding" element={<Suspense fallback={<AdminFallback />}><AdminSettings /></Suspense>} />
            <Route path="settings/billing" element={<Suspense fallback={<AdminFallback />}><AdminSettings /></Suspense>} />
            <Route path="settings/integrations" element={<Suspense fallback={<AdminFallback />}><AdminSettings /></Suspense>} />
          </Route>

          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />
            <Route path="chat" element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />
            <Route path="chat/:sessionId" element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />
            <Route path="projects" element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />
            <Route path="video-studio" element={<VideoStudio />} />
          </Route>

          <Route path="/labs" element={<DashboardLayout />}>
            <Route index element={<LabsHome />} />
            <Route path="chat/:sessionId" element={<Suspense fallback={<AdminFallback />}><AdminChatHome /></Suspense>} />
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
