import { useState, useEffect, useCallback } from 'react';
import {
  Folder, File, Search, ChevronRight, Home, Trash2,
  Copy, Clipboard, ArrowUp, Download, Eye, RefreshCw,
} from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { FileItem } from '@/types';
import toast from 'react-hot-toast';

function formatSize(bytes: number): string {
  if (bytes === 0) return '--';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export default function FileManagerPage() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [currentPath, setCurrentPath] = useState('');
  const [breadcrumbs, setBreadcrumbs] = useState<{ name: string; path: string }[]>([]);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<FileItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<{ name: string; content: string } | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const fetchFiles = useCallback(async (path: string) => {
    setLoading(true);
    setSelected(new Set());
    try {
      const { data } = await api.get('/files', { params: { path } });
      const list = data?.items || data || [];
      setFiles(list);
      const parts = path ? path.split('/').filter(Boolean) : [];
      setBreadcrumbs(parts.map((p, i) => ({
        name: p,
        path: parts.slice(0, i + 1).join('/'),
      })));
    } catch {
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles(currentPath);
  }, [currentPath, fetchFiles]);

  const handleSearch = useCallback(async () => {
    if (!search.trim()) { setSearchResults(null); return; }
    try {
      const { data } = await api.get('/files/search', { params: { q: search } });
      setSearchResults(data?.items || data || []);
    } catch {
      setSearchResults([]);
    }
  }, [search]);

  const handleClick = (item: FileItem) => {
    if (item.type === 'directory') {
      setCurrentPath(item.path);
    } else {
      openPreview(item);
    }
  };

  const openPreview = async (item: FileItem) => {
    try {
      const { data } = await api.get('/files/read', { params: { path: item.path } });
      setPreview({ name: item.name, content: data.content });
    } catch {
      toast.error('Cannot preview this file');
    }
  };

  const handleDelete = async (path: string) => {
    if (!confirm('Move this item to trash?')) return;
    try {
      await api.delete('/files', { params: { path } });
      toast.success('Moved to trash');
      fetchFiles(currentPath);
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleCopy = async (path: string) => {
    try {
      await api.post('/files/copy', { source: path });
      toast.success('Copied');
      fetchFiles(currentPath);
    } catch {
      toast.error('Copy failed');
    }
  };

  const handleRename = async (item: FileItem) => {
    const name = prompt('New name:', item.name);
    if (!name || name === item.name) return;
    try {
      await api.post('/files/rename', { source: item.path, name });
      toast.success('Renamed');
      fetchFiles(currentPath);
    } catch {
      toast.error('Rename failed');
    }
  };

  const items = searchResults ?? files;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Toolbar */}
      <div className="glass rounded-xl p-4">
        <div className="flex items-center gap-3">
          <button onClick={() => setCurrentPath('')} className="rounded-lg p-2 text-gray-400 hover:bg-white/10">
            <Home className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-1 text-sm text-gray-500">
            <button onClick={() => setCurrentPath('')} className="hover:text-white">workspace</button>
            {breadcrumbs.map((b) => (
              <span key={b.path} className="flex items-center gap-1">
                <ChevronRight className="h-3 w-3" />
                <button onClick={() => setCurrentPath(b.path)} className="hover:text-white">{b.name}</button>
              </span>
            ))}
          </div>
          <div className="flex-1" />
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search files..."
              className="w-64 rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
            />
          </div>
          <button onClick={() => fetchFiles(currentPath)} className="rounded-lg p-2 text-gray-400 hover:bg-white/10">
            <RefreshCw className={clsx('h-4 w-4', loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* File list */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-medium uppercase tracking-wider text-gray-500 border-b border-white/5">
          <div className="col-span-6">Name</div>
          <div className="col-span-2">Size</div>
          <div className="col-span-3">Modified</div>
          <div className="col-span-1"></div>
        </div>
        {loading ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">Loading...</div>
        ) : items.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">
            {searchResults !== null ? 'No search results' : 'Empty directory'}
          </div>
        ) : items.map((item) => (
          <div
            key={item.path}
            className={clsx(
              'grid grid-cols-12 gap-2 px-4 py-3 items-center text-sm transition-all hover:bg-white/[0.03] cursor-pointer border-b border-white/[0.03]',
              selected.has(item.path) && 'bg-blue-500/10',
            )}
            onClick={() => handleClick(item)}
          >
            <div className="col-span-6 flex items-center gap-3 min-w-0">
              {item.type === 'directory' ? (
                <Folder className="h-4 w-4 flex-shrink-0 text-blue-400" />
              ) : (
                <File className="h-4 w-4 flex-shrink-0 text-gray-500" />
              )}
              <span className="truncate text-white">{item.name}</span>
            </div>
            <div className="col-span-2 text-gray-500">{item.type === 'file' ? formatSize(item.size) : '--'}</div>
            <div className="col-span-3 text-gray-500">
              {item.modified ? format(new Date(item.modified), 'MMM d, HH:mm') : '--'}
            </div>
            <div className="col-span-1 flex justify-end gap-1">
              <button onClick={(e) => { e.stopPropagation(); handleCopy(item.path); }} className="rounded p-1 text-gray-600 hover:text-white hover:bg-white/10"><Copy className="h-3 w-3" /></button>
              <button onClick={(e) => { e.stopPropagation(); handleDelete(item.path); }} className="rounded p-1 text-gray-600 hover:text-red-400 hover:bg-white/10"><Trash2 className="h-3 w-3" /></button>
            </div>
          </div>
        ))}
      </div>

      {/* Preview modal */}
      {preview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setPreview(null)}>
          <div className="glass max-h-[80vh] w-full max-w-3xl overflow-hidden rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <span className="text-sm font-medium text-white">{preview.name}</span>
              <button onClick={() => setPreview(null)} className="text-gray-400 hover:text-white">✕</button>
            </div>
            <pre className="overflow-auto p-4 text-sm text-gray-300 font-mono max-h-[60vh] whitespace-pre-wrap">{preview.content}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
