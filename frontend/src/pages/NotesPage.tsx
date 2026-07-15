import NotesPanel from '@/components/NotesPanel';

export default function NotesPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Notes</h1>
      <NotesPanel />
    </div>
  );
}
