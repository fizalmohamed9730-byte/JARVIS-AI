import { useState, useEffect, useCallback } from 'react';
import { Plus, Pin, Search, Tag, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { Note } from '@/types';

export default function NotesPanel() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  const fetchNotes = useCallback(async () => {
    try {
      const { data } = await api.get('/notes');
      setNotes(data.map((n: Record<string, unknown>) => ({
        id: String(n.id),
        title: n.title as string,
        content: n.content as string,
        tags: (n.tags as string[]) || [],
        pinned: n.is_pinned as boolean,
        color: 'border-blue-500/30',
        createdAt: n.created_at as string,
        updatedAt: n.updated_at as string,
      })));
    } catch {
      setNotes([]);
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const allTags = [...new Set(notes.flatMap((n) => n.tags))];

  const filtered = notes.filter((n) => {
    const matchesSearch = !search || n.title.toLowerCase().includes(search.toLowerCase()) || n.content.toLowerCase().includes(search.toLowerCase());
    const matchesTag = !selectedTag || n.tags.includes(selectedTag);
    return matchesSearch && matchesTag;
  });

  const pinned = filtered.filter((n) => n.pinned);
  const unpinned = filtered.filter((n) => !n.pinned);

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      {/* Search + Tags */}
      <div className="glass rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search notes..."
              className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
            />
          </div>
          <button
            onClick={async () => {
              try {
                const { data } = await api.post('/notes', { title: 'New Note', content: '', tags: [] });
                setNotes((prev) => [{
                  id: String(data.id),
                  title: data.title,
                  content: data.content,
                  tags: data.tags || [],
                  pinned: data.is_pinned,
                  color: 'border-blue-500/30',
                  createdAt: data.created_at,
                  updatedAt: data.updated_at,
                }, ...prev]);
              } catch { /* ignore */ }
            }}
            className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
          >
            <Plus className="h-4 w-4" />
            New Note
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
              className={clsx(
                'flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-all',
                selectedTag === tag ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-400 hover:bg-white/10',
              )}
            >
              <Tag className="h-3 w-3" />
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Pinned Notes */}
      {pinned.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 px-1 text-xs font-medium uppercase tracking-wider text-gray-500">
            <Pin className="h-3 w-3" />
            Pinned
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {pinned.map((note) => (
              <NoteCard key={note.id} note={note} onDelete={async () => {
                try { await api.delete(`/notes/${note.id}`); setNotes((prev) => prev.filter((n) => n.id !== note.id)); } catch { /* ignore */ }
              }} />
            ))}
          </div>
        </div>
      )}

      {/* Other Notes */}
      {unpinned.length > 0 && (
        <div>
          <h3 className="mb-2 px-1 text-xs font-medium uppercase tracking-wider text-gray-500">Notes</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {unpinned.map((note) => (
              <NoteCard key={note.id} note={note} onDelete={async () => {
                try { await api.delete(`/notes/${note.id}`); setNotes((prev) => prev.filter((n) => n.id !== note.id)); } catch { /* ignore */ }
              }} />
            ))}
          </div>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="glass rounded-xl p-8 text-center">
          <p className="text-sm text-gray-500">No notes found</p>
        </div>
      )}
    </div>
  );
}

function NoteCard({ note, onDelete }: { note: Note; onDelete?: () => void }) {
  return (
    <div className={clsx('glass group cursor-pointer rounded-xl p-4 transition-all hover:bg-white/[0.07]', note.color)}>
      <div className="flex items-start justify-between">
        <h4 className="text-sm font-medium text-white">{note.title}</h4>
        <button onClick={onDelete} className="rounded p-1 text-gray-600 opacity-0 transition-all hover:text-red-400 group-hover:opacity-100">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <p className="mt-2 line-clamp-3 text-xs text-gray-400">{note.content}</p>
      <div className="mt-3 flex items-center justify-between">
        <div className="flex gap-1">
          {note.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-gray-500">{tag}</span>
          ))}
        </div>
        <span className="text-[10px] text-gray-600">{format(new Date(note.updatedAt), 'MMM d')}</span>
      </div>
    </div>
  );
}
