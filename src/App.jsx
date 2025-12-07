import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import HomePage from './components/HomePage';
import OurStory from './pages/OurStory';
import WhatWeWant from './pages/WhatWeWant';
import About from './pages/About';
import Terms from './pages/Terms';
import Privacy from './pages/Privacy';
import UploadPage from './pages/UploadPage';
import ManifestoPage from './pages/ManifestoPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/our-story" element={<OurStory />} />
            <Route path="/what-we-want" element={<WhatWeWant />} />
            <Route path="/about" element={<About />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/manifesto" element={<ManifestoPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-black text-white py-8 mt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <div className="palestine-flag-stripe mb-4"></div>
              <div className="flex items-center justify-center gap-2 mb-4">
                <div className="pa-emblem">PA</div>
                <span className="text-xl font-bold">Palestine Accountability</span>
              </div>
              <p className="text-gray-300 mb-4">
                Documenting state oppression • Defending democratic rights • 🇵🇸 Free Palestine
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
      </div>
    </Router>
  );
}

export default App;

