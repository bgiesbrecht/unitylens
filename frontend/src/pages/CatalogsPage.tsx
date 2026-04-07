import { useState } from 'react';
import { BookOpen, Layers, Table2, Columns, Database, RefreshCw } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getCatalogsDetail, getSources } from '../api/client';
import type { CatalogDetail } from '../api/client';
import type { Source } from '../types';
import { CardSkeleton } from '../components/Skeleton';
import { EmptyState } from '../components/EmptyState';
import { useRouter } from '../router';

function StatPill({ icon, value, label }: { icon: React.ReactNode; value: number; label: string }) {
  return (
    <div className="catalog-stat-pill">
      {icon}
      <span className="catalog-stat-value">{value.toLocaleString()}</span>
      <span className="catalog-stat-label">{label}</span>
    </div>
  );
}

export function CatalogsPage() {
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const { data: sources } = useApi(getSources);
  const { data: catalogs, loading, error, refetch } = useApi(
    () => getCatalogsDetail(sourceFilter || undefined),
    [sourceFilter]
  );
  const { navigate } = useRouter();

  const totalSchemas = catalogs?.reduce((s, c) => s + c.schema_count, 0) ?? 0;
  const totalTables = catalogs?.reduce((s, c) => s + c.table_count, 0) ?? 0;
  const totalColumns = catalogs?.reduce((s, c) => s + c.column_count, 0) ?? 0;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-header-title">Catalogs</h1>
          <p className="page-header-desc">
            All data catalogs across your connected sources
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            className="catalog-filter-select"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="">All Sources</option>
            {sources?.map((s: Source) => (
              <option key={s.name} value={s.name}>{s.name}</option>
            ))}
          </select>
          <button className="btn btn-secondary" onClick={refetch}>
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary bar */}
      {catalogs && catalogs.length > 0 && (
        <div className="catalog-summary-bar">
          <StatPill icon={<BookOpen size={14} />} value={catalogs.length} label="Catalogs" />
          <StatPill icon={<Layers size={14} />} value={totalSchemas} label="Schemas" />
          <StatPill icon={<Table2 size={14} />} value={totalTables} label="Tables" />
          <StatPill icon={<Columns size={14} />} value={totalColumns} label="Columns" />
        </div>
      )}

      {error && (
        <div className="card" style={{ marginBottom: 20, padding: '16px 24px', borderColor: 'var(--status-red)', background: 'var(--status-red-bg)' }}>
          <p style={{ color: 'var(--status-red)', fontSize: '0.9rem' }}>Failed to load catalogs: {error}</p>
        </div>
      )}

      {loading ? (
        <div className="catalog-grid">
          <CardSkeleton /><CardSkeleton /><CardSkeleton />
        </div>
      ) : catalogs && catalogs.length > 0 ? (
        <div className="catalog-grid">
          {catalogs.map((cat: CatalogDetail) => (
            <div
              key={cat.full_name}
              className="card card-clickable catalog-card"
              onClick={() => navigate(`/browse?source=${encodeURIComponent(cat.source_name)}&catalog=${encodeURIComponent(cat.catalog_name)}`)}
            >
              <div className="catalog-card-header">
                <div className="catalog-card-icon">
                  <BookOpen size={20} />
                </div>
                <div>
                  <div className="catalog-card-name">{cat.catalog_name}</div>
                  <div className="catalog-card-source">
                    <Database size={12} style={{ marginRight: 4, opacity: 0.5 }} />
                    {cat.source_name}
                  </div>
                </div>
              </div>

              {cat.comment && (
                <p className="catalog-card-comment">{cat.comment}</p>
              )}

              {cat.owner && (
                <div className="catalog-card-owner">
                  Owner: {cat.owner}
                </div>
              )}

              <div className="catalog-card-counts">
                <div className="catalog-card-count">
                  <span className="catalog-card-count-value">{cat.schema_count}</span>
                  <span className="catalog-card-count-label">Schemas</span>
                </div>
                <div className="catalog-card-count">
                  <span className="catalog-card-count-value">{cat.table_count}</span>
                  <span className="catalog-card-count-label">Tables</span>
                </div>
                <div className="catalog-card-count">
                  <span className="catalog-card-count-value">{cat.column_count}</span>
                  <span className="catalog-card-count-label">Columns</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<BookOpen size={48} />}
          title="No catalogs found"
          description="Run a crawl from the Admin page to discover catalogs from your data sources."
        />
      )}
    </div>
  );
}
