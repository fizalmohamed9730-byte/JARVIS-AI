import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Mail, Lock, User, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { api } from '@/utils/api';
import toast from 'react-hot-toast';

type Mode = 'login' | 'register';

export default function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('login');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    fullName: '',
  });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'login') {
        const { data } = await api.post('/auth/login', {
          email: form.email,
          password: form.password,
        });
        localStorage.setItem('jarvis_token', data.access_token);
        toast.success('Welcome back!');
        navigate('/');
      } else {
        await api.post('/auth/register', {
          username: form.username,
          email: form.email,
          password: form.password,
          full_name: form.fullName,
        });
        toast.success('Account created! Please log in.');
        setMode('login');
        setForm((p) => ({ ...p, password: '' }));
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Something went wrong';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-64px)] items-center justify-center p-4" style={{ background: 'var(--bg-base)' }}>
      <div
        className="w-full max-w-md rounded-2xl p-8"
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl" style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>JARVIS</h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg px-4 py-3 text-sm" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
                <input
                  required
                  value={form.username}
                  onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))}
                  className="w-full rounded-lg py-2.5 pl-10 pr-3 text-sm outline-none"
                  style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                  placeholder="johndoe"
                />
              </div>
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                className="w-full rounded-lg py-2.5 pl-10 pr-3 text-sm outline-none"
                style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                placeholder="john@example.com"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                required
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
                className="w-full rounded-lg py-2.5 pl-10 pr-10 text-sm outline-none"
                style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                placeholder="••••••••"
                minLength={6}
              />
              <button
                type="button"
                onClick={() => setShowPassword((p) => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--text-muted)' }}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {mode === 'register' && (
            <div>
              <label className="mb-1 block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Full Name (optional)</label>
              <input
                value={form.fullName}
                onChange={(e) => setForm((p) => ({ ...p, fullName: e.target.value }))}
                className="w-full rounded-lg px-3 py-2.5 text-sm outline-none"
                style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                placeholder="John Doe"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
          >
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        {/* Toggle mode */}
        <div className="mt-6 text-center">
          <button
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
            className="text-sm font-medium transition-opacity hover:opacity-80"
            style={{ color: 'var(--accent)' }}
          >
            {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </button>
        </div>

        {/* Back link */}
        <div className="mt-4 text-center">
          <button
            onClick={() => navigate('/')}
            className="text-xs transition-opacity hover:opacity-80"
            style={{ color: 'var(--text-muted)' }}
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
