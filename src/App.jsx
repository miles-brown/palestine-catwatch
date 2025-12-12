import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home, Upload, LayoutDashboard, Search, Shield, LogIn } from 'lucide-react';
import Header from './components/Header';
import HomePage from './components/HomePage';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute, { AdminRoute } from './components/ProtectedRoute';
import PalestineRibbon from './components/PalestineRibbon';
import { AuthProvider, useAuth } from './context/AuthContext';
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
import ProtestDatabasePage from './pages/ProtestDatabasePage';
import ChainOfCommandPage from './pages/ChainOfCommandPage';
import OfficerProfilePage from './pages/OfficerProfilePage';
import GeographicPage from './pages/GeographicPage';
import EquipmentCorrelationPage from './pages/EquipmentCorrelationPage';
import TimelinePage from './pages/TimelinePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import './App.css';

// Mobile Bottom Navigation Component - Auth-aware
const MobileNav = () => {
  const location = useLocation();
  const { isAuthenticated, isAdmin } = useAuth();
  const isActive = (path) => location.pathname === path;

  // Dynamic nav items based on auth state
  const navItems = [
    { path: '/', icon: Home, label: 'Home', show: true },
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', show: isAuthenticated },
    { path: '/upload', icon: Upload, label: 'Upload', show: isAuthenticated },
    { path: '/face-search', icon: Search, label: 'Search', show: isAuthenticated },
    { path: '/admin', icon: Shield, label: 'Admin', show: isAdmin },
    { path: '/login', icon: LogIn, label: 'Login', show: !isAuthenticated },
  ].filter(item => item.show);

  // Limit to 5 items max
  const visibleItems = navItems.slice(0, 5);
  const gridCols = Math.min(visibleItems.length, 5);

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden z-50 pb-safe">
      <div
        className="h-16"
        style={{ display: 'grid', gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}
      >
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center justify-center gap-1 transition-colors ${
                active ? 'text-slate-900' : 'text-gray-500'
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

// Main App Content - separated to allow useAuth hook usage
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
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/report/:mediaId" element={<ReportPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/face-search" element={<ProtectedRoute><FaceSearchPage /></ProtectedRoute>} />
            <Route path="/equipment" element={<ProtectedRoute><EquipmentPage /></ProtectedRoute>} />
            <Route path="/protests" element={<ProtectedRoute><ProtestDatabasePage /></ProtectedRoute>} />
            <Route path="/chain-of-command" element={<ProtectedRoute><ChainOfCommandPage /></ProtectedRoute>} />
            <Route path="/officer/:officerId" element={<ProtectedRoute><OfficerProfilePage /></ProtectedRoute>} />
            <Route path="/geographic" element={<ProtectedRoute><GeographicPage /></ProtectedRoute>} />
            <Route path="/equipment-correlation" element={<ProtectedRoute><EquipmentCorrelationPage /></ProtectedRoute>} />
            <Route path="/timeline" element={<ProtectedRoute><TimelinePage /></ProtectedRoute>} />

            {/* Admin Only Routes */}
            <Route path="/admin" element={<AdminRoute><AdminPage /></AdminRoute>} />
          </Routes>
          </ErrorBoundary>
        </main>

        {/* Footer - Hidden on mobile to make room for bottom nav */}
        <footer className="bg-slate-900 text-white py-12 mt-16 hidden md:block">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
              {/* Brand */}
              <div className="md:col-span-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className="relative">
                    <div className="flex items-center justify-center w-8 h-8 rounded bg-white text-slate-900 font-bold text-xs">
                      PAC
                    </div>
                  </div>
                  <span className="font-semibold">Palestine Accountability</span>
                  {/* Solidarity ribbon */}
                  <PalestineRibbon size="md" className="ml-1" />
                </div>
                <p className="text-sm text-slate-400">
                  An independent research initiative documenting police conduct at public demonstrations in the UK.
                </p>
                <p className="text-xs text-slate-500 mt-3 flex items-center gap-2">
                  <span>In solidarity with Palestine</span>
                  <span className="text-base">🇵🇸</span>
                </p>
              </div>

              {/* Research */}
              <div>
                <h4 className="font-semibold text-sm uppercase tracking-wider text-slate-400 mb-4">Research</h4>
                <ul className="space-y-2 text-sm">
                  <li><Link to="/protests" className="text-slate-300 hover:text-white transition-colors">Protest Database</Link></li>
                  <li><Link to="/equipment" className="text-slate-300 hover:text-white transition-colors">Equipment Records</Link></li>
                  <li><Link to="/timeline" className="text-slate-300 hover:text-white transition-colors">Event Timeline</Link></li>
                  <li><Link to="/geographic" className="text-slate-300 hover:text-white transition-colors">Geographic Analysis</Link></li>
                </ul>
              </div>

              {/* About */}
              <div>
                <h4 className="font-semibold text-sm uppercase tracking-wider text-slate-400 mb-4">About</h4>
                <ul className="space-y-2 text-sm">
                  <li><Link to="/our-story" className="text-slate-300 hover:text-white transition-colors">Our Mission</Link></li>
                  <li><Link to="/what-we-want" className="text-slate-300 hover:text-white transition-colors">Our Goals</Link></li>
                  <li><Link to="/about" className="text-slate-300 hover:text-white transition-colors">Methodology</Link></li>
                  <li><Link to="/manifesto" className="text-slate-300 hover:text-white transition-colors">Our Approach</Link></li>
                </ul>
              </div>

              {/* Legal */}
              <div>
                <h4 className="font-semibold text-sm uppercase tracking-wider text-slate-400 mb-4">Legal</h4>
                <ul className="space-y-2 text-sm">
                  <li><Link to="/terms" className="text-slate-300 hover:text-white transition-colors">Terms of Use</Link></li>
                  <li><Link to="/privacy" className="text-slate-300 hover:text-white transition-colors">Privacy Policy</Link></li>
                </ul>
              </div>
            </div>

            {/* Bottom Bar */}
            <div className="pt-8 border-t border-slate-800">
              <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                <p className="text-sm text-slate-400">
                  &copy; {new Date().getFullYear()} Palestine Accountability Campaign. Independent research project.
                </p>
                <p className="text-xs text-slate-500">
                  This project operates within UK law. All data is collected from public sources.
                </p>
              </div>
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

