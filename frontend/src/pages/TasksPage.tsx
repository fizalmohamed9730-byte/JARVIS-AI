import TaskPanel from '@/components/TaskPanel';

export default function TasksPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Tasks</h1>
      <TaskPanel />
    </div>
  );
}
