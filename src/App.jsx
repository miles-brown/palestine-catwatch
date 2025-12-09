import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home, Upload, LayoutDashboard, Search, Shield } from 'lucide-react';
import Header from './components/Header';
import HomePage from './components/HomePage';
import ErrorBoundary from './components/ErrorBoundary';
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
import './App.css';

// Mobile Bottom Navigation Component
const MobileNav = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/upload', icon: Upload, label: 'Upload' },
    { path: '/face-search', icon: Search, label: 'Search' },
    { path: '/admin', icon: Shield, label: 'Admin' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden z-50 pb-safe">
      <div className="grid grid-cols-5 h-16">
        {navItems.map((item) => {
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

function App() {
  return (
    <ErrorBoundary>
    <Router>
      <div className="min-h-screen bg-gray-50 pb-16 md:pb-0">
        <Header />
        <main>
          <ErrorBoundary fallbackMessage="This page encountered an error. Please try again.">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/our-story" element={<OurStory />} />
            <Route path="/what-we-want" element={<WhatWeWant />} />
            <Route path="/about" element={<About />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/report/:mediaId" element={<ReportPage />} />
            <Route path="/manifesto" element={<ManifestoPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/face-search" element={<FaceSearchPage />} />
            <Route path="/equipment" element={<EquipmentPage />} />
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
                Documenting state oppression • Defending democratic rights • Free Palestine
              </p>
              <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-400">
                <span>For press freedom</span>
                <span>•</span>
                <span>Against fascism</span>
                <span>•</span>
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
    </ErrorBoundary>
  );
}

export default App;

