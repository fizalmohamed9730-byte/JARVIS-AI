import { useState, useEffect, useCallback } from 'react';
import { Search, Trash2, Brain } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { Memory } from '@/types';

const categoryColors: Record<string, string> = {
  preference: 'bg-blue-500/15 text-blue-400',
  fact: 'bg-green-500/15 text-green-400',
  habit: 'bg-purple-500/15 text-purple-400',
  relationship: 'bg-orange-500/15 text-orange-400',
  context: 'bg-cyan-500/15 text-cyan-400',
};

export default function MemoryViewer() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<string>('all');

  const fetchMemories = useCallback(async () => {
    try {
      if (search) {
        const { data } = await api.get('/memory/search', { params: { q: search } });
        setMemories(data.map((m: Record<string, unknown>) => ({
          id: String(m.id),
          category: (m.category as string) || 'context',
          key: (m.content as string)?.slice(0, 40) || '',
          value: (m.content as string) || '',
          confidence: 0.9,
          source: (m.source as string) || 'database',
          createdAt: (m.created_at as string) || new Date().toISOString(),
          updatedAt: (m.created_at as string) || new Date().toISOString(),
        })));
      } else {
        const { data: cats } = await api.get('/memory/categories');
        const allMems: Memory[] = [];
        for (const cat of cats) {
          const { data } = await api.get('/memory/search', { params: { q: cat } });
          for (const m of data) {
            allMems.push({
              id: String(m.id),
              category: (m.category as string) || cat,
              key: (m.content as string)?.slice(0, 40) || '',
              value: (m.content as string) || '',
              confidence: 0.9,
              source: (m.source as string) || 'database',
              createdAt: (m.created_at as string) || new Date().toISOString(),
              updatedAt: (m.created_at as string) || new Date().toISOString(),
            });
          }
        }
        setMemories(allMems);
      }
    } catch {
      setMemories([]);
    }
  }, [search]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const categories = ['all', ...new Set(memories.map((m) => m.category))];

  const filtered = memories.filter((m) => {
    const matchesSearch = !search || m.key.toLowerCase().includes(search.toLowerCase()) || m.value.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' || m.category === filter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="glass rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search memories..."
              className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
            />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={clsx(
                'rounded-full px-3 py-1 text-xs font-medium transition-all',
                filter === cat ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-400 hover:bg-white/10',
              )}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((memory) => (
          <div key={memory.id} className="glass group rounded-xl p-4 transition-all hover:bg-white/[0.07]">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-white/5">
                  <Brain className="h-4 w-4 text-blue-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{memory.key}</span>
                    <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium', categoryColors[memory.category])}>
                      {memory.category}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-400">{memory.value}</p>
                  <div className="mt-2 flex items-center gap-3 text-[10px] text-gray-600">
                    <span>Confidence: {Math.round(memory.confidence * 100)}%</span>
                    <span>Source: {memory.source}</span>
                    <span>Updated: {format(new Date(memory.updatedAt), 'MMM d, yyyy')}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={async (ev) => {
                  ev.stopPropagation();
                  try {
                    await api.delete(`/memory/${memory.id}`);
                    setMemories((prev) => prev.filter((m) => m.id !== memory.id));
                  } catch { /* ignore */ }
                }}
                className="rounded p-1 text-gray-600 opacity-0 transition-all hover:text-red-400 group-hover:opacity-100"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
