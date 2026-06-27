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
import Academy from "@/pages/Academy";
import CourseDetail from "@/pages/CourseDetail";
import Learn from "@/pages/Learn";
import Studio from "@/pages/Studio";
import Pricing from "@/pages/Pricing";
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
import MediaStudio from "@/pages/MediaStudio";
import StorefrontLayout from "@/components/StorefrontLayout";
import LearnLayout from "@/components/LearnLayout";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
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
            <Route path="/academy" element={<Academy />} />
            <Route path="/academy/:slug" element={<CourseDetail />} />
            <Route path="/pricing" element={<Pricing />} />
          </Route>
          <Route element={<LearnLayout />}>
            <Route path="/academy/:slug/learn" element={<Learn />} />
            <Route path="/studio" element={<Studio />} />
            <Route path="/studio/media" element={<MediaStudio />} />
          </Route>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="products" element={<AdminProducts />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="suppliers" element={<AdminSuppliers />} />
            <Route path="customers" element={<AdminCustomers />} />
            <Route path="courses" element={<AdminCourses />} />
            <Route path="sourcing" element={<AdminSourcing />} />
            <Route path="deploy" element={<AdminDeploy />} />
            <Route path="ai-ops" element={<AdminAiOps />} />
            <Route path="chat" element={<AdminAIChat />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}
