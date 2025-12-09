import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home, Upload, LayoutDashboard, Search, Shield, LogIn } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import HomePage from './components/HomePage';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute, { AdminRoute, ContributorRoute } from './components/ProtectedRoute';
import OurStory from './pages/OurStory';
import WhatWeWant from './pages/WhatWeWant';
import About from './pages/About';
import Terms from './pages/Terms';
import Privacy from './pages/Privacy';
import UploadPage from './pages/UploadPage';
import ReportPage from './pages/ReportPage';
import ManifestoPage from './pages/ManifestoPage';
import DashboardPage from './pages/DashboardPage';
import AdminPage from './pages/AdminPage';
import FaceSearchPage from './pages/FaceSearchPage';
import EquipmentPage from './pages/EquipmentPage';
import ChainOfCommandPage from './pages/ChainOfCommandPage';
import OfficerProfilePage from './pages/OfficerProfilePage';
import GeographicPage from './pages/GeographicPage';
import EquipmentCorrelationPage from './pages/EquipmentCorrelationPage';
import TimelinePage from './pages/TimelinePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import './App.css';

// Mobile Bottom Navigation Component
const MobileNav = () => {
  const location = useLocation();
  const { isAuthenticated, isAdmin } = useAuth();
  const isActive = (path) => location.pathname === path;

  const navItems = [
    { path: '/', icon: Home, label: 'Home', show: true },
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', show: isAuthenticated },
    { path: '/upload', icon: Upload, label: 'Upload', show: isAuthenticated },
    { path: '/face-search', icon: Search, label: 'Search', show: isAuthenticated },
    { path: '/admin', icon: Shield, label: 'Admin', show: isAdmin },
    { path: '/login', icon: LogIn, label: 'Login', show: !isAuthenticated },
  ].filter(item => item.show);

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden z-50 pb-safe">
      <div className={`grid grid-cols-${Math.min(navItems.length, 5)} h-16`}>
        {navItems.slice(0, 5).map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center justify-center gap-1 transition-colors ${
                active ? 'text-green-600' : 'text-gray-500'
              }`}
            >
              <Icon className={`h-5 w-5 ${active ? 'stroke-[2.5px]' : ''}`} />
              <span className="text-[10px] font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
};

// Main App Content (needs to be inside AuthProvider)
const AppContent = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 pb-16 md:pb-0">
        <Header />
        <main>
          <ErrorBoundary fallbackMessage="This page encountered an error. Please try again.">
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/our-story" element={<OurStory />} />
            <Route path="/what-we-want" element={<WhatWeWant />} />
            <Route path="/about" element={<About />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/manifesto" element={<ManifestoPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Routes - Require Authentication */}
            <Route path="/upload" element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            } />
            <Route path="/report/:mediaId" element={
              <ProtectedRoute>
                <ReportPage />
              </ProtectedRoute>
            } />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } />
            <Route path="/face-search" element={
              <ProtectedRoute>
                <FaceSearchPage />
              </ProtectedRoute>
            } />
            <Route path="/equipment" element={
              <ProtectedRoute>
                <EquipmentPage />
              </ProtectedRoute>
            } />
            <Route path="/chain-of-command" element={
              <ProtectedRoute>
                <ChainOfCommandPage />
              </ProtectedRoute>
            } />
            <Route path="/officer/:officerId" element={
              <ProtectedRoute>
                <OfficerProfilePage />
              </ProtectedRoute>
            } />
            <Route path="/geographic" element={
              <ProtectedRoute>
                <GeographicPage />
              </ProtectedRoute>
            } />
            <Route path="/equipment-correlation" element={
              <ProtectedRoute>
                <EquipmentCorrelationPage />
              </ProtectedRoute>
            } />
            <Route path="/timeline" element={
              <ProtectedRoute>
                <TimelinePage />
              </ProtectedRoute>
            } />

            {/* Admin Only Routes */}
            <Route path="/admin" element={
              <AdminRoute>
                <AdminPage />
              </AdminRoute>
            } />
          </Routes>
          </ErrorBoundary>
        </main>

        {/* Footer - Hidden on mobile to make room for bottom nav */}
        <footer className="bg-black text-white py-8 mt-16 hidden md:block">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <div className="palestine-flag-stripe mb-4"></div>
              <div className="flex items-center justify-center gap-2 mb-4">
                <div className="pa-emblem">PA</div>
                <span className="text-xl font-bold">Palestine Accountability</span>
              </div>
              <p className="text-gray-300 mb-4">
                Documenting state oppression - Defending democratic rights - Free Palestine
              </p>
              <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-400">
                <span>For press freedom</span>
                <span>-</span>
                <span>Against fascism</span>
                <span>-</span>
                <span>In memory of fallen journalists</span>
              </div>
              <p className="text-xs text-gray-500 mt-4">
                "The truth will set you free, but first it will piss you off" - Gloria Steinem
              </p>
            </div>
          </div>
        </footer>

        {/* Mobile Bottom Navigation */}
        <MobileNav />
      </div>
    </Router>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
