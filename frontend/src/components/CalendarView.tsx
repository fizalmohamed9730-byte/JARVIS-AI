import { useState, useEffect, useCallback } from 'react';
import {
  startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval,
  format, isSameMonth, isSameDay, isToday, addMonths, subMonths,
} from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import { api } from '@/utils/api';

interface CalEvent {
  id: string;
  title: string;
  date: Date;
  color: string;
}

const EVENT_COLORS = ['bg-blue-500', 'bg-green-500', 'bg-red-500', 'bg-yellow-500', 'bg-purple-500', 'bg-pink-500'];

export default function CalendarView() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [events, setEvents] = useState<CalEvent[]>([]);

  const fetchEvents = useCallback(async () => {
    try {
      const start = startOfMonth(currentMonth).toISOString();
      const end = endOfMonth(currentMonth).toISOString();
      const { data } = await api.get('/calendar', { params: { start, end } });
      const mapped: CalEvent[] = data.map((e: Record<string, unknown>, i: number) => ({
        id: String(e.id),
        title: e.title as string,
        date: new Date(e.start_time as string),
        color: EVENT_COLORS[i % EVENT_COLORS.length],
      }));
      setEvents(mapped);
    } catch {
      setEvents([]);
    }
  }, [currentMonth]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const calStart = startOfWeek(monthStart);
  const calEnd = endOfWeek(monthEnd);
  const days = eachDayOfInterval({ start: calStart, end: calEnd });

  const eventsOnDay = (day: Date) => events.filter((e) => isSameDay(e.date, day));

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="glass mb-4 flex items-center justify-between rounded-xl px-4 py-3">
        <button
          onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
          className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <h2 className="text-lg font-semibold text-white">{format(currentMonth, 'MMMM yyyy')}</h2>
        <button
          onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
          className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Day names */}
      <div className="mb-2 grid grid-cols-7 gap-1">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <div key={d} className="py-2 text-center text-xs font-medium text-gray-500">{d}</div>
        ))}
      </div>

      {/* Days grid */}
      <div className="glass rounded-xl p-2">
        <div className="grid grid-cols-7 gap-1">
          {days.map((day) => {
            const events = eventsOnDay(day);
            const isCurrentMonth = isSameMonth(day, currentMonth);
            const isSelected = isSameDay(day, selectedDate);
            const today = isToday(day);

            return (
              <button
                key={day.toISOString()}
                onClick={() => setSelectedDate(day)}
                className={clsx(
                  'relative flex flex-col items-center rounded-lg p-2 transition-all',
                  isCurrentMonth ? 'text-white' : 'text-gray-600',
                  isSelected && 'bg-blue-500/20 ring-1 ring-blue-500/50',
                  today && !isSelected && 'bg-white/5',
                  'hover:bg-white/10',
                )}
              >
                <span className={clsx(
                  'text-sm',
                  today && 'font-bold text-blue-400',
                )}>
                  {format(day, 'd')}
                </span>
                {events.length > 0 && (
                  <div className="mt-1 flex gap-0.5">
                    {events.slice(0, 3).map((e) => (
                      <div key={e.id} className={clsx('h-1.5 w-1.5 rounded-full', e.color)} />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected day events */}
      <div className="mt-4 glass rounded-xl p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-300">
          {format(selectedDate, 'EEEE, MMMM d')}
        </h3>
        {eventsOnDay(selectedDate).length === 0 ? (
          <p className="text-xs text-gray-500">No events</p>
        ) : (
          <div className="space-y-2">
            {eventsOnDay(selectedDate).map((event) => (
              <div key={event.id} className="flex items-center gap-3 rounded-lg bg-white/5 px-3 py-2">
                <div className={clsx('h-2 w-2 rounded-full', event.color)} />
                <span className="text-sm text-gray-200">{event.title}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
