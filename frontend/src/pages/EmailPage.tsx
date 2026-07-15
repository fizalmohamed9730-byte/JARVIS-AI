import EmailPanel from '@/components/EmailPanel';

export default function EmailPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Email</h1>
      <EmailPanel />
    </div>
  );
}
