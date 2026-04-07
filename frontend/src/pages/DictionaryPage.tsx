import { useState, useEffect, useCallback } from 'react';
import { Search, ChevronDown, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight, BookOpen } from 'lucide-react';
import { Skeleton } from '../components/Skeleton';
import { EmptyState } from '../components/EmptyState';

interface DictColumn {
  column_name: string;
  data_type: string;
  is_nullable: number;
  comment: string;
}

interface DictTable {
  source_name: string;
  catalog_name: string;
  schema_name: string;
  table_name: string;
  full_name: string;
  table_type: string;
  comment: string;
  owner: string;
  column_count: number;
  columns: DictColumn[];
}

interface DictResponse {
  tables: DictTable[];
  total: number;
  offset: number;
  limit: number;
  filters: {
    sources: string[];
    catalogs: string[];
    schemas: string[];
  };
}

const PAGE_SIZE = 50;

export function DictionaryPage() {
  const [data, setData] = useState<DictResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sourceFilter, setSourceFilter] = useState('');
  const [catalogFilter, setCatalogFilter] = useState('');
  const [schemaFilter, setSchemaFilter] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(0);

  // Expanded rows
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (sourceFilter) params.set('source', sourceFilter);
      if (catalogFilter) params.set('catalog', catalogFilter);
      if (schemaFilter) params.set('schema', schemaFilter);
      if (searchFilter) params.set('search', searchFilter);
      params.set('offset', String(page * PAGE_SIZE));
      params.set('limit', String(PAGE_SIZE));

      const resp = await fetch(`/api/dictionary?${params}`);
      if (!resp.ok) throw new Error(`API error ${resp.status}`);
      const json: DictResponse = await resp.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [sourceFilter, catalogFilter, schemaFilter, searchFilter, page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const toggleRow = (fullName: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(fullName)) next.delete(fullName);
      else next.add(fullName);
      return next;
    });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setSearchFilter(searchInput);
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-header-title">Data Dictionary</h1>
        <p className="page-header-desc">
          Complete reference of all tables and columns across your data catalog
        </p>
      </div>

      {/* Filter bar */}
      <div className="dict-filter-bar">
        <form onSubmit={handleSearch} className="dict-search-form">
          <Search size={14} className="dict-search-icon" />
          <input
            type="text"
            className="dict-search-input"
            placeholder="Filter tables..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </form>

        <select
          className="dict-filter-select"
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(0); }}
        >
          <option value="">All Sources</option>
          {data?.filters.sources.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        <select
          className="dict-filter-select"
          value={catalogFilter}
          onChange={(e) => { setCatalogFilter(e.target.value); setPage(0); }}
        >
          <option value="">All Catalogs</option>
          {data?.filters.catalogs.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        <select
          className="dict-filter-select"
          value={schemaFilter}
          onChange={(e) => { setSchemaFilter(e.target.value); setPage(0); }}
        >
          <option value="">All Schemas</option>
          {data?.filters.schemas.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        {data && (
          <span className="dict-count">
            {data.total.toLocaleString()} table{data.total !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {error && (
        <div className="card" style={{ marginBottom: 16, padding: '12px 20px', borderColor: 'var(--status-red)', background: 'var(--status-red-bg)' }}>
          <p style={{ color: 'var(--status-red)', fontSize: '0.85rem', margin: 0 }}>{error}</p>
        </div>
      )}

      {loading && !data ? (
        <div style={{ padding: 20 }}><Skeleton variant="text" count={12} /></div>
      ) : data && data.tables.length > 0 ? (
        <>
          <div className="dict-table-wrap">
            <table className="dict-table">
              <thead>
                <tr>
                  <th style={{ width: 32 }}></th>
                  <th>Table</th>
                  <th>Catalog</th>
                  <th>Schema</th>
                  <th>Type</th>
                  <th>Owner</th>
                  <th style={{ width: 60 }}>Cols</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {data.tables.map((tbl) => {
                  const isExpanded = expanded.has(tbl.full_name);
                  return (
                    <TableRow
                      key={tbl.full_name}
                      table={tbl}
                      expanded={isExpanded}
                      onToggle={() => toggleRow(tbl.full_name)}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="dict-pagination">
              <button
                className="btn btn-secondary btn-sm"
                disabled={page === 0}
                onClick={() => setPage(0)}
              >
                <ChevronsLeft size={14} />
              </button>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft size={14} />
              </button>
              <span className="dict-page-info">
                Page {page + 1} of {totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight size={14} />
              </button>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage(totalPages - 1)}
              >
                <ChevronsRight size={14} />
              </button>
            </div>
          )}
        </>
      ) : (
        <EmptyState
          icon={<BookOpen size={48} />}
          title="No tables found"
          description={searchFilter || sourceFilter || catalogFilter || schemaFilter
            ? "No tables match your current filters. Try adjusting them."
            : "Run a crawl to populate the data dictionary."}
        />
      )}
    </div>
  );
}

function TableRow({
  table,
  expanded,
  onToggle,
}: {
  table: DictTable;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr className={`dict-row ${expanded ? 'dict-row-expanded' : ''}`} onClick={onToggle}>
        <td className="dict-expand-cell">
          {table.column_count > 0 && (
            expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          )}
        </td>
        <td className="dict-table-name">{table.table_name}</td>
        <td className="dict-dim">{table.catalog_name}</td>
        <td className="dict-dim">{table.schema_name}</td>
        <td><span className="dict-type-badge">{table.table_type}</span></td>
        <td className="dict-dim">{table.owner || '--'}</td>
        <td className="dict-col-count">{table.column_count}</td>
        <td className="dict-comment">{table.comment || '--'}</td>
      </tr>
      {expanded && table.columns.length > 0 && (
        <tr className="dict-columns-row">
          <td></td>
          <td colSpan={7}>
            <div className="dict-columns-wrap">
              <table className="dict-columns-table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Data Type</th>
                    <th>Nullable</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {table.columns.map((col, i) => (
                    <tr key={i}>
                      <td className="dict-col-name">{col.column_name}</td>
                      <td className="dict-col-type">{col.data_type}</td>
                      <td className="dict-col-nullable">{col.is_nullable ? 'Yes' : 'No'}</td>
                      <td className="dict-col-comment">{col.comment || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
