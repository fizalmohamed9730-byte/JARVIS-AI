import { useState, useEffect, useCallback } from 'react';
import { Globe, Trash2, Code, Eye, Download, Wand2, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { WebsiteProject } from '@/types';
import toast from 'react-hot-toast';

const STYLES = ['modern', 'minimal', 'portfolio', 'business', 'creative'];

export default function WebsiteGeneratorPage() {
  const [projects, setProjects] = useState<WebsiteProject[]>([]);
  const [prompt, setPrompt] = useState('');
  const [style, setStyle] = useState('modern');
  const [darkMode, setDarkMode] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selected, setSelected] = useState<WebsiteProject | null>(null);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [activeFile, setActiveFile] = useState(0);

  const fetchProjects = useCallback(async () => {
    try {
      const { data } = await api.get('/websites');
      setProjects(data?.items || data || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    try {
      const { data } = await api.post('/websites', {
        prompt, style, dark_mode: darkMode, pages: ['home', 'about', 'contact'],
      });
      setProjects((prev) => [data, ...prev]);
      setSelected(data);
      toast.success('Website generated');
    } catch {
      toast.error('Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/websites/${id}`);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      if (selected?.id === id) setSelected(null);
      toast.success('Project deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Generator */}
      <div className="glass rounded-xl p-6">
        <h3 className="mb-4 text-sm font-semibold text-white">Generate Website</h3>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the website you want to generate..."
          rows={3}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50 resize-none"
        />
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-gray-500">Style</label>
            <div className="flex gap-1">
              {STYLES.map((s) => (
                <button
                  key={s}
                  onClick={() => setStyle(s)}
                  className={clsx(
                    'rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                    style === s ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-400 hover:bg-white/10',
                  )}
                >{s}</button>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-400">
            <input type="checkbox" checked={darkMode} onChange={(e) => setDarkMode(e.target.checked)} className="accent-blue-500" />
            Dark mode
          </label>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || !prompt.trim()}
          className="mt-4 flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {generating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Globe className="h-4 w-4" />}
          {generating ? 'Generating...' : 'Generate Website'}
        </button>
      </div>

      <div className="flex gap-4">
        {/* Project list */}
        <div className="w-64 flex-shrink-0 space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500 mb-2">Projects ({projects.length})</h3>
          {projects.length === 0 ? (
            <div className="glass rounded-xl p-4 text-center text-sm text-gray-500">No projects yet</div>
          ) : projects.map((p) => (
            <div
              key={p.id}
              onClick={() => { setSelected(p); setActiveFile(0); }}
              className={clsx(
                'glass cursor-pointer rounded-xl p-3 transition-all hover:bg-white/[0.07]',
                selected?.id === p.id && 'ring-2 ring-blue-500/50',
              )}
            >
              <p className="text-sm font-medium text-white truncate">{p.prompt.slice(0, 40)}</p>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[10px] text-gray-500">{p.style} | {format(new Date(p.created_at), 'MMM d')}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                  className="rounded p-1 text-gray-600 opacity-0 hover:text-red-400 group-hover:opacity-100"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Preview / Code */}
        {selected && (
          <div className="flex-1 glass rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2">
              <button
                onClick={() => setViewMode('preview')}
                className={clsx('rounded-lg px-3 py-1 text-xs font-medium', viewMode === 'preview' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:bg-white/10')}
              ><Eye className="mr-1 inline h-3 w-3" />Preview</button>
              <button
                onClick={() => setViewMode('code')}
                className={clsx('rounded-lg px-3 py-1 text-xs font-medium', viewMode === 'code' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:bg-white/10')}
              ><Code className="mr-1 inline h-3 w-3" />Code</button>
              <div className="flex-1" />
              <span className="text-[10px] text-gray-500">{selected.files?.length || 0} files</span>
            </div>
            {viewMode === 'preview' ? (
              <div className="h-[500px] bg-white">
                <iframe
                  srcDoc={selected.preview_html}
                  className="h-full w-full border-0"
                  title="Preview"
                />
              </div>
            ) : (
              <div className="flex h-[500px]">
                <div className="w-40 border-r border-white/10 overflow-y-auto">
                  {selected.files?.map((f, i) => (
                    <button
                      key={f.filename}
                      onClick={() => setActiveFile(i)}
                      className={clsx(
                        'block w-full px-3 py-2 text-left text-xs',
                        i === activeFile ? 'bg-blue-500/10 text-blue-400' : 'text-gray-400 hover:bg-white/5',
                      )}
                    >
                      {f.filename}
                    </button>
                  ))}
                </div>
                <pre className="flex-1 overflow-auto p-4 text-xs text-gray-300 font-mono">
                  {selected.files?.[activeFile]?.content || ''}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
