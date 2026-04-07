import { useState, useEffect, useRef } from 'react';
import {
  Database,
  BookOpen,
  Layers,
  Table2,
  ChevronRight,
  ChevronDown,
  Columns,
} from 'lucide-react';
import { getSources, getCatalogs, getSchemas, getTables, getTableDetail } from '../api/client';
import { Breadcrumb, type BreadcrumbItem } from '../components/Breadcrumb';
import { DataTable } from '../components/DataTable';
import { EmptyState } from '../components/EmptyState';
import { Skeleton, TableSkeleton } from '../components/Skeleton';
import type { Source, Catalog, Schema, Table, Column } from '../types';

interface TreeNode {
  id: string;
  type: 'source' | 'catalog' | 'schema' | 'table';
  name: string;
  source?: string;
  catalog?: string;
  schema?: string;
  children?: TreeNode[];
  expanded?: boolean;
  loading?: boolean;
}

interface Selection {
  source?: string;
  catalog?: string;
  schema?: string;
  table?: string;
}

function nodeId(node: { type: string; name: string; source?: string; catalog?: string; schema?: string }) {
  return `${node.type}:${node.source || ''}:${node.catalog || ''}:${node.schema || ''}:${node.name}`;
}

function deepUpdate(nodes: TreeNode[], targetId: string, updates: Partial<TreeNode>): TreeNode[] {
  return nodes.map((node) => {
    if (node.id === targetId) {
      return { ...node, ...updates };
    }
    if (node.children) {
      return { ...node, children: deepUpdate(node.children, targetId, updates) };
    }
    return node;
  });
}

export function BrowsePage({ params }: { params: Record<string, string> }) {
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [treeLoading, setTreeLoading] = useState(true);
  const [selection, setSelection] = useState<Selection>({});
  const [detail, setDetail] = useState<Table | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Load top-level sources on mount, then auto-expand from URL params
  useEffect(() => {
    // Parse URL params
    const hash = window.location.hash.slice(1);
    const qIdx = hash.indexOf('?');
    let initSource = '';
    let initCatalog = '';
    if (qIdx >= 0) {
      const sp = new URLSearchParams(hash.slice(qIdx + 1));
      initSource = sp.get('source') || '';
      initCatalog = sp.get('catalog') || '';
    }

    setTreeLoading(true);
    getSources()
      .then(async (sources: Source[]) => {
        let nodes: TreeNode[] = sources.map((s) => ({
          id: nodeId({ type: 'source', name: s.name }),
          type: 'source' as const,
          name: s.name,
          expanded: false,
        }));

        // Auto-expand source if specified
        if (initSource) {
          const srcIdx = nodes.findIndex((n) => n.name === initSource);
          if (srcIdx >= 0) {
            try {
              const catalogs = await getCatalogs(initSource);
              const catChildren: TreeNode[] = catalogs.map((c: Catalog) => ({
                id: nodeId({ type: 'catalog', name: c.name, source: initSource }),
                type: 'catalog' as const,
                name: c.name,
                source: initSource,
              }));
              nodes = nodes.map((n, i) =>
                i === srcIdx ? { ...n, expanded: true, children: catChildren } : n
              );
              setSelection({ source: initSource });

              // Auto-expand catalog if specified
              if (initCatalog) {
                const catNode = catChildren.find((c) => c.name === initCatalog);
                if (catNode) {
                  try {
                    const schemas = await getSchemas(initSource, initCatalog);
                    const schChildren: TreeNode[] = schemas.map((s: Schema) => ({
                      id: nodeId({ type: 'schema', name: s.name, source: initSource, catalog: initCatalog }),
                      type: 'schema' as const,
                      name: s.name,
                      source: initSource,
                      catalog: initCatalog,
                    }));
                    // Update the catalog node within the source's children
                    const updatedCatChildren = catChildren.map((c) =>
                      c.name === initCatalog ? { ...c, expanded: true, children: schChildren } : c
                    );
                    nodes = nodes.map((n, i) =>
                      i === srcIdx ? { ...n, expanded: true, children: updatedCatChildren } : n
                    );
                    setSelection({ source: initSource, catalog: initCatalog });
                  } catch { /* ignore */ }
                }
              }
            } catch { /* ignore */ }
          }
        }

        setTree(nodes);
      })
      .catch(() => setTree([]))
      .finally(() => setTreeLoading(false));
  }, []);

  async function handleToggle(node: TreeNode) {
    if (node.expanded) {
      setTree((prev) => deepUpdate(prev, node.id, { expanded: false }));
      return;
    }

    if (node.children) {
      setTree((prev) => deepUpdate(prev, node.id, { expanded: true }));
      return;
    }

    // Load children
    setTree((prev) => deepUpdate(prev, node.id, { loading: true, expanded: true }));

    try {
      let children: TreeNode[] = [];
      if (node.type === 'source') {
        const catalogs = await getCatalogs(node.name);
        children = catalogs.map((c: Catalog) => ({
          id: nodeId({ type: 'catalog', name: c.name, source: node.name }),
          type: 'catalog' as const,
          name: c.name,
          source: node.name,
        }));
      } else if (node.type === 'catalog') {
        const schemas = await getSchemas(node.source!, node.name);
        children = schemas.map((s: Schema) => ({
          id: nodeId({ type: 'schema', name: s.name, source: node.source, catalog: node.name }),
          type: 'schema' as const,
          name: s.name,
          source: node.source,
          catalog: node.name,
        }));
      } else if (node.type === 'schema') {
        const tables = await getTables(node.source!, node.catalog!, node.name);
        children = tables.map((t: Table) => ({
          id: nodeId({ type: 'table', name: t.name, source: node.source, catalog: node.catalog, schema: node.name }),
          type: 'table' as const,
          name: t.name,
          source: node.source,
          catalog: node.catalog,
          schema: node.name,
        }));
      }
      setTree((prev) => deepUpdate(prev, node.id, { children, loading: false }));
    } catch {
      setTree((prev) => deepUpdate(prev, node.id, { loading: false, children: [] }));
    }
  }

  async function handleSelect(node: TreeNode) {
    const newSelection: Selection = {};
    if (node.type === 'source') {
      newSelection.source = node.name;
    } else if (node.type === 'catalog') {
      newSelection.source = node.source;
      newSelection.catalog = node.name;
    } else if (node.type === 'schema') {
      newSelection.source = node.source;
      newSelection.catalog = node.catalog;
      newSelection.schema = node.name;
    } else if (node.type === 'table') {
      newSelection.source = node.source;
      newSelection.catalog = node.catalog;
      newSelection.schema = node.schema;
      newSelection.table = node.name;
    }
    setSelection(newSelection);

    if (node.type === 'table') {
      setDetailLoading(true);
      try {
        const d = await getTableDetail(node.source!, node.catalog!, node.schema!, node.name);
        setDetail(d);
      } catch {
        setDetail(null);
      } finally {
        setDetailLoading(false);
      }
    } else {
      setDetail(null);
      handleToggle(node);
    }
  }

  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'All Sources', onClick: () => setSelection({}) },
  ];
  if (selection.source) {
    breadcrumbs.push({
      label: selection.source,
      onClick: () => setSelection({ source: selection.source }),
    });
  }
  if (selection.catalog) {
    breadcrumbs.push({
      label: selection.catalog,
      onClick: () => setSelection({ source: selection.source, catalog: selection.catalog }),
    });
  }
  if (selection.schema) {
    breadcrumbs.push({
      label: selection.schema,
      onClick: () => setSelection({
        source: selection.source,
        catalog: selection.catalog,
        schema: selection.schema,
      }),
    });
  }
  if (selection.table) {
    breadcrumbs.push({ label: selection.table });
  }

  const columnDefs = [
    {
      key: 'position',
      header: '#',
      width: '50px',
      render: (row: Column) => (
        <span style={{ color: 'var(--text-tertiary)' }}>{row.position ?? ''}</span>
      ),
    },
    { key: 'name', header: 'Column Name' },
    {
      key: 'type',
      header: 'Type',
      render: (row: Column) => <span className="col-type">{row.type}</span>,
    },
    {
      key: 'nullable',
      header: 'Nullable',
      render: (row: Column) => (
        <span className="col-nullable">{row.nullable ? 'Yes' : 'No'}</span>
      ),
    },
    {
      key: 'comment',
      header: 'Comment',
      render: (row: Column) => (
        <span style={{ color: row.comment ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>
          {row.comment || '--'}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-header-title">Browse Catalog</h1>
        <p className="page-header-desc">
          Navigate your data hierarchy: Source / Catalog / Schema / Table
        </p>
      </div>

      <Breadcrumb items={breadcrumbs} />

      <div className="browse-layout">
        <div className="tree-panel">
          <div className="tree-panel-header">Catalog Explorer</div>
          <div className="tree-panel-body">
            {treeLoading ? (
              <div style={{ padding: 12 }}>
                <Skeleton variant="text" count={6} />
              </div>
            ) : tree.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
                No sources available
              </div>
            ) : (
              tree.map((node) => (
                <TreeBranch
                  key={node.id}
                  node={node}
                  depth={0}
                  selection={selection}
                  onSelect={handleSelect}
                  onToggle={handleToggle}
                />
              ))
            )}
          </div>
        </div>

        <div className="detail-panel">
          {detailLoading ? (
            <div className="detail-panel-body">
              <Skeleton variant="text-lg" />
              <div style={{ height: 16 }} />
              <TableSkeleton rows={6} />
            </div>
          ) : detail ? (
            <>
              <div className="detail-panel-header">
                <div className="detail-panel-title">{detail.name}</div>
                <div className="detail-panel-subtitle">
                  {detail.source} / {detail.catalog} / {detail.schema}
                </div>
              </div>
              <div className="detail-panel-body">
                <div className="detail-meta">
                  {detail.type && (
                    <div className="detail-meta-item">
                      <span className="detail-meta-label">Type</span>
                      <span className="detail-meta-value">{detail.type}</span>
                    </div>
                  )}
                  {detail.owner && (
                    <div className="detail-meta-item">
                      <span className="detail-meta-label">Owner</span>
                      <span className="detail-meta-value">{detail.owner}</span>
                    </div>
                  )}
                  {detail.description && (
                    <div className="detail-meta-item" style={{ gridColumn: 'span 2' }}>
                      <span className="detail-meta-label">Description</span>
                      <span className="detail-meta-value">{detail.description}</span>
                    </div>
                  )}
                </div>

                {detail.columns && detail.columns.length > 0 && (
                  <>
                    <div className="detail-section-title">
                      <Columns size={14} style={{ marginRight: 8, verticalAlign: -2 }} />
                      Columns ({detail.columns.length})
                    </div>
                    <DataTable columns={columnDefs} data={detail.columns as Column[]} />
                  </>
                )}
              </div>
            </>
          ) : (
            <EmptyState
              icon={<Table2 size={48} />}
              title="Select a table"
              description="Choose a table from the catalog explorer on the left to view its details and columns."
            />
          )}
        </div>
      </div>
    </div>
  );
}

function TreeBranch({
  node,
  depth,
  selection,
  onSelect,
  onToggle,
}: {
  node: TreeNode;
  depth: number;
  selection: Selection;
  onSelect: (node: TreeNode) => void;
  onToggle: (node: TreeNode) => void;
}) {
  const isActive =
    (node.type === 'source' && selection.source === node.name && !selection.catalog) ||
    (node.type === 'catalog' && selection.catalog === node.name && !selection.schema) ||
    (node.type === 'schema' && selection.schema === node.name && !selection.table) ||
    (node.type === 'table' && selection.table === node.name);

  const hasChildren = node.type !== 'table';
  const icon = getNodeIcon(node.type);
  const depthClass = depth > 0 ? `tree-indent-${Math.min(depth, 3)}` : '';

  return (
    <>
      <div
        className={`tree-item ${depthClass} ${isActive ? 'active' : ''}`}
        onClick={() => onSelect(node)}
      >
        {hasChildren && (
          <span style={{ width: 14, display: 'flex', flexShrink: 0 }}>
            {node.loading ? (
              <span className="spinner spinner-sm" />
            ) : node.expanded ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronRight size={14} />
            )}
          </span>
        )}
        {!hasChildren && <span style={{ width: 14 }} />}
        {icon}
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {node.name}
        </span>
      </div>
      {node.expanded &&
        node.children?.map((child) => (
          <TreeBranch
            key={child.id}
            node={child}
            depth={depth + 1}
            selection={selection}
            onSelect={onSelect}
            onToggle={onToggle}
          />
        ))}
    </>
  );
}

function getNodeIcon(type: string) {
  const style = { width: 16, height: 16, flexShrink: 0, opacity: 0.6 } as const;
  switch (type) {
    case 'source':
      return <Database style={{ ...style, color: 'var(--accent)' }} />;
    case 'catalog':
      return <BookOpen style={{ ...style, color: '#7c3aed' }} />;
    case 'schema':
      return <Layers style={{ ...style, color: '#d97706' }} />;
    case 'table':
      return <Table2 style={{ ...style, color: 'var(--status-green)' }} />;
    default:
      return null;
  }
}
