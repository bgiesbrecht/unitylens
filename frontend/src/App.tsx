import { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { RouterProvider, Routes, useRouter } from './router';
import { Sidebar } from './components/Sidebar';
import { SearchBar } from './components/SearchBar';
import { DashboardPage } from './pages/DashboardPage';
import { SourcesPage } from './pages/SourcesPage';
import { BrowsePage } from './pages/BrowsePage';
import { SearchPage } from './pages/SearchPage';
import { AdminPage } from './pages/AdminPage';
import { DictionaryPage } from './pages/DictionaryPage';
import { LoginPage } from './pages/LoginPage';
import { AuthProvider, useAuth } from './auth/AuthContext';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/sources': 'Data Sources',
  '/dictionary': 'Data Dictionary',
  '/browse': 'Browse Catalog',
  '/search': 'Search',
  '/admin': 'Administration',
};

const ADMIN_ROUTES = [
  { pattern: '/', component: DashboardPage },
  { pattern: '/sources', component: SourcesPage },
  { pattern: '/dictionary', component: DictionaryPage },
  { pattern: '/browse', component: BrowsePage },
  { pattern: '/search', component: SearchPage },
  { pattern: '/admin', component: AdminPage },
];

const VIEWER_ROUTES = [
  { pattern: '/', component: DictionaryPage },
  { pattern: '/dictionary', component: DictionaryPage },
  { pattern: '/browse', component: BrowsePage },
  { pattern: '/search', component: SearchPage },
];

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { path, navigate } = useRouter();
  const { user } = useAuth();

  // Close sidebar on navigation (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [path]);

  // Redirect viewers away from admin-only pages.
  useEffect(() => {
    if (!user) return;
    const basePath = path.split('?')[0];
    if (user.role === 'viewer') {
      const allowed = new Set(['/dictionary', '/browse', '/search']);
      if (!allowed.has(basePath)) {
        navigate('/dictionary');
      }
    }
  }, [user, path, navigate]);

  const basePath = path.split('?')[0];
  const pageTitle = PAGE_TITLES[basePath] || 'UnityLens';
  const routes = user?.role === 'admin' ? ADMIN_ROUTES : VIEWER_ROUTES;

  return (
    <div className="app-layout">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main-area">
        <header className="header">
          <button
            className="mobile-menu-btn"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
          <span className="header-title">{pageTitle}</span>
          <SearchBar compact placeholder="Search catalog..." />
          <div className="header-right">
            {user && (
              <span style={{ fontSize: '0.78rem', opacity: 0.7 }}>
                {user.username} · {user.role}
              </span>
            )}
          </div>
        </header>
        <main className="content">
          <Routes routes={routes} />
        </main>
      </div>
    </div>
  );
}

function AuthGate() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <span className="spinner" />
      </div>
    );
  }
  if (!user) return <LoginPage />;
  return <AppLayout />;
}

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider>
        <AuthGate />
      </RouterProvider>
    </AuthProvider>
  );
}
