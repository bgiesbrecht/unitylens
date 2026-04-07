import {
  LayoutDashboard,
  Database,
  FolderTree,
  Search,
  Settings,
  ScanSearch,
  BookOpen,
  TableProperties,
} from 'lucide-react';
import { Link } from '../router';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/sources', icon: Database, label: 'Sources' },
  { to: '/catalogs', icon: BookOpen, label: 'Catalogs' },
  { to: '/dictionary', icon: TableProperties, label: 'Data Dictionary' },
  { to: '/browse', icon: FolderTree, label: 'Browse Catalog' },
  { to: '/search', icon: Search, label: 'Search' },
];

const ADMIN_ITEMS = [
  { to: '/admin', icon: Settings, label: 'Admin' },
];

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && <div className="sidebar-overlay" onClick={onClose} />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <ScanSearch size={18} />
          </div>
          <div>
            <div className="sidebar-brand-text">UnityLens</div>
            <div className="sidebar-brand-sub">Data Catalog</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-nav-section">Navigation</div>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="sidebar-link"
              activeClassName="active"
              onClick={onClose}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          ))}

          <div className="sidebar-nav-section" style={{ marginTop: 12 }}>
            Administration
          </div>
          {ADMIN_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="sidebar-link"
              activeClassName="active"
              onClick={onClose}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          UnityLens v0.1.0
        </div>
      </aside>
    </>
  );
}
