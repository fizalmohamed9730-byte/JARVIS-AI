import { useState, useEffect, useCallback } from 'react';
import { Image as ImageIcon, Trash2, Download, Wand2, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { GeneratedImage } from '@/types';
import toast from 'react-hot-toast';

const STYLES = ['natural', 'artistic', 'photorealistic', 'anime', 'pixel'];
const SIZES = ['512x512', '1024x1024', '1024x768', '768x1024'];

export default function ImageGenerationPage() {
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [prompt, setPrompt] = useState('');
  const [style, setStyle] = useState('natural');
  const [size, setSize] = useState('1024x1024');
  const [provider, setProvider] = useState('local');
  const [generating, setGenerating] = useState(false);
  const [selected, setSelected] = useState<GeneratedImage | null>(null);

  const fetchImages = useCallback(async () => {
    try {
      const { data } = await api.get('/images');
      const list = data?.items || data || [];
      setImages(list);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchImages(); }, [fetchImages]);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    try {
      const { data } = await api.post('/images', { prompt, style, size, provider });
      setImages((prev) => [data, ...prev]);
      setSelected(data);
      toast.success('Image generated');
    } catch {
      toast.error('Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/images/${id}`);
      setImages((prev) => prev.filter((i) => i.id !== id));
      if (selected?.id === id) setSelected(null);
      toast.success('Image deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Generator */}
      <div className="glass rounded-xl p-6">
        <h3 className="mb-4 text-sm font-semibold text-white">Generate Image</h3>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the image you want to generate..."
          rows={3}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50 resize-none"
        />
        <div className="mt-3 flex flex-wrap gap-3">
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
          <div>
            <label className="mb-1 block text-xs text-gray-500">Size</label>
            <select
              value={size}
              onChange={(e) => setSize(e.target.value)}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white outline-none"
            >
              {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating || !prompt.trim()}
          className="mt-4 flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {generating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
          {generating ? 'Generating...' : 'Generate'}
        </button>
      </div>

      <div className="flex gap-4">
        {/* Gallery */}
        <div className="flex-1">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-500">Gallery ({images.length})</h3>
          {images.length === 0 ? (
            <div className="glass rounded-xl p-8 text-center text-sm text-gray-500">
              <ImageIcon className="mx-auto mb-3 h-8 w-8 text-gray-600" />
              No images generated yet
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
              {images.map((img) => (
                <div
                  key={img.id}
                  onClick={() => setSelected(img)}
                  className={clsx(
                    'glass group cursor-pointer overflow-hidden rounded-xl transition-all hover:bg-white/[0.07]',
                    selected?.id === img.id && 'ring-2 ring-blue-500/50',
                  )}
                >
                  <div className="aspect-square bg-white/5 flex items-center justify-center overflow-hidden">
                    <img src={img.url} alt={img.prompt} className="w-full h-full object-cover" />
                  </div>
                  <div className="p-3">
                    <p className="text-xs text-white truncate">{img.prompt}</p>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-[10px] text-gray-500">{format(new Date(img.created_at), 'MMM d, HH:mm')}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(img.id); }}
                        className="rounded p-1 text-gray-600 opacity-0 hover:text-red-400 group-hover:opacity-100"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detail */}
        {selected && (
          <div className="w-80 flex-shrink-0">
            <div className="glass rounded-xl p-4 sticky top-4">
              <div className="aspect-square overflow-hidden rounded-lg bg-white/5">
                <img src={selected.url} alt={selected.prompt} className="w-full h-full object-contain" />
              </div>
              <p className="mt-3 text-sm text-white">{selected.prompt}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-gray-500">
                <span>{selected.style}</span>
                <span>{selected.size}</span>
                <span>{selected.provider}</span>
                <span>{format(new Date(selected.created_at), 'MMM d, yyyy HH:mm')}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
