import CalendarView from '@/components/CalendarView';

export default function CalendarPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Calendar</h1>
      <CalendarView />
    </div>
  );
}
