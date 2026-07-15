import { useState, useEffect, useCallback } from 'react';
import { Film, Trash2, Play, Plus, RefreshCw, ChevronDown, ChevronRight, Wand2 } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { VideoProject, VideoScene } from '@/types';
import toast from 'react-hot-toast';

const STYLES = ['professional', 'casual', 'cinematic', 'animated'];
const DURATIONS = ['short', 'medium', 'long'];

export default function VideoWorkflowPage() {
  const [projects, setProjects] = useState<VideoProject[]>([]);
  const [selected, setSelected] = useState<VideoProject | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [script, setScript] = useState('');
  const [style, setStyle] = useState('professional');
  const [duration, setDuration] = useState('short');
  const [creating, setCreating] = useState(false);
  const [expandedScenes, setExpandedScenes] = useState<Set<number>>(new Set([1]));

  const fetchProjects = useCallback(async () => {
    try {
      const { data } = await api.get('/video');
      setProjects(data?.items || data || []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const { data } = await api.post('/video', { title, description, script, style, duration });
      setProjects((prev) => [data, ...prev]);
      setSelected(data);
      setShowCreate(false);
      setTitle(''); setDescription(''); setScript('');
      toast.success('Video project created');
    } catch {
      toast.error('Creation failed');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this video project?')) return;
    try {
      await api.delete(`/video/${id}`);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      if (selected?.id === id) setSelected(null);
      toast.success('Project deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleGenerate = async (id: string) => {
    try {
      await api.post(`/video/${id}/generate`);
      setProjects((prev) => prev.map((p) => p.id === id ? { ...p, status: 'generating', progress: 10 } : p));
      if (selected?.id === id) setSelected((s) => s ? { ...s, status: 'generating', progress: 10 } : s);
      toast.success('Video generation started');
    } catch {
      toast.error('Generation failed');
    }
  };

  const toggleScene = (num: number) => {
    setExpandedScenes((prev) => {
      const next = new Set(prev);
      if (next.has(num)) next.delete(num); else next.add(num);
      return next;
    });
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Video Workflow</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
        >
          <Plus className="h-4 w-4" /> New Project
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="glass rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white">Create Video Project</h3>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Video title..."
            className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)..."
            rows={2}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50 resize-none"
          />
          <textarea
            value={script}
            onChange={(e) => setScript(e.target.value)}
            placeholder="Script or outline (AI will generate storyboard)..."
            rows={5}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50 resize-none"
          />
          <div className="flex gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-500">Style</label>
              <div className="flex gap-1">
                {STYLES.map((s) => (
                  <button key={s} onClick={() => setStyle(s)} className={clsx('rounded-lg px-3 py-1.5 text-xs font-medium transition-all', style === s ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-400 hover:bg-white/10')}>{s}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">Duration</label>
              <div className="flex gap-1">
                {DURATIONS.map((d) => (
                  <button key={d} onClick={() => setDuration(d)} className={clsx('rounded-lg px-3 py-1.5 text-xs font-medium transition-all', duration === d ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-400 hover:bg-white/10')}>{d}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={creating || !title.trim()} className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50">
              {creating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
              {creating ? 'Creating...' : 'Create with AI Storyboard'}
            </button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:bg-white/5">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex gap-4">
        {/* Project list */}
        <div className="w-72 flex-shrink-0 space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500 mb-2">Projects ({projects.length})</h3>
          {projects.length === 0 ? (
            <div className="glass rounded-xl p-6 text-center text-sm text-gray-500">
              <Film className="mx-auto mb-3 h-6 w-6 text-gray-600" />
              No video projects yet
            </div>
          ) : projects.map((p) => (
            <div
              key={p.id}
              onClick={() => setSelected(p)}
              className={clsx('glass cursor-pointer rounded-xl p-3 transition-all hover:bg-white/[0.07]', selected?.id === p.id && 'ring-2 ring-blue-500/50')}
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white truncate">{p.title}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium',
                      p.status === 'completed' ? 'bg-green-500/15 text-green-400' :
                      p.status === 'generating' ? 'bg-yellow-500/15 text-yellow-400' :
                      'bg-white/10 text-gray-400'
                    )}>{p.status}</span>
                    <span className="text-[10px] text-gray-500">{p.scenes?.length || 0} scenes</span>
                  </div>
                </div>
                <div className="flex gap-1">
                  {p.status === 'draft' && (
                    <button onClick={(e) => { e.stopPropagation(); handleGenerate(p.id); }} className="rounded p-1 text-gray-600 hover:text-green-400"><Play className="h-3 w-3" /></button>
                  )}
                  <button onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }} className="rounded p-1 text-gray-600 hover:text-red-400"><Trash2 className="h-3 w-3" /></button>
                </div>
              </div>
              {p.status === 'generating' && (
                <div className="mt-2 h-1 rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${p.progress}%` }} />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Storyboard */}
        {selected && (
          <div className="flex-1 glass rounded-xl p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">{selected.title}</h3>
                <p className="text-xs text-gray-500">{selected.description || 'No description'}</p>
              </div>
              <div className="flex gap-2">
                {selected.status === 'draft' && (
                  <button onClick={() => handleGenerate(selected.id)} className="flex items-center gap-2 rounded-lg bg-green-500/20 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/30">
                    <Play className="h-3 w-3" /> Generate Video
                  </button>
                )}
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-gray-400">{selected.style} | {selected.duration}</span>
              </div>
            </div>

            <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-500">Storyboard ({selected.scenes?.length || 0} scenes)</h4>
            <div className="space-y-2">
              {(selected.scenes || []).map((scene) => (
                <div key={scene.scene_number} className="rounded-xl border border-white/5 bg-white/[0.02]">
                  <button
                    onClick={() => toggleScene(scene.scene_number)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/15 text-xs font-bold text-blue-400">
                      {scene.scene_number}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">{scene.title}</p>
                      <p className="text-xs text-gray-500 truncate">{scene.description}</p>
                    </div>
                    <span className="text-[10px] text-gray-600">{scene.duration_seconds}s</span>
                    {expandedScenes.has(scene.scene_number) ? <ChevronDown className="h-4 w-4 text-gray-500" /> : <ChevronRight className="h-4 w-4 text-gray-500" />}
                  </button>
                  {expandedScenes.has(scene.scene_number) && (
                    <div className="border-t border-white/5 px-4 py-3 space-y-2">
                      <div>
                        <span className="text-[10px] font-medium uppercase text-gray-500">Narration</span>
                        <p className="text-xs text-gray-300 mt-0.5">{scene.narration}</p>
                      </div>
                      <div>
                        <span className="text-[10px] font-medium uppercase text-gray-500">Visual</span>
                        <p className="text-xs text-gray-300 mt-0.5">{scene.visual_prompt}</p>
                      </div>
                      <div className="flex gap-3 text-[10px] text-gray-600">
                        <span>Transition: {scene.transition}</span>
                        <span>Duration: {scene.duration_seconds}s</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
