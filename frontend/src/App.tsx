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
import { CatalogsPage } from './pages/CatalogsPage';
import { DictionaryPage } from './pages/DictionaryPage';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/sources': 'Data Sources',
  '/catalogs': 'Catalogs',
  '/dictionary': 'Data Dictionary',
  '/browse': 'Browse Catalog',
  '/search': 'Search',
  '/admin': 'Administration',
};

const ROUTES = [
  { pattern: '/', component: DashboardPage },
  { pattern: '/sources', component: SourcesPage },
  { pattern: '/catalogs', component: CatalogsPage },
  { pattern: '/dictionary', component: DictionaryPage },
  { pattern: '/browse', component: BrowsePage },
  { pattern: '/search', component: SearchPage },
  { pattern: '/admin', component: AdminPage },
];

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { path } = useRouter();

  // Close sidebar on navigation (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [path]);

  // Get page title from path (strip query params)
  const basePath = path.split('?')[0];
  const pageTitle = PAGE_TITLES[basePath] || 'UnityLens';

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
            {/* Placeholder for future user menu */}
          </div>
        </header>
        <main className="content">
          <Routes routes={ROUTES} />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <RouterProvider>
      <AppLayout />
    </RouterProvider>
  );
}
