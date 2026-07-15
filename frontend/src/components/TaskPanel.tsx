import { useState } from 'react';
import { useTasks } from '@/hooks/useTasks';
import { Plus, Calendar, Flag, Trash2, Filter } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import type { Task } from '@/types';

const priorityColors: Record<string, string> = {
  low: 'text-gray-400 bg-gray-500/10',
  medium: 'text-yellow-400 bg-yellow-500/10',
  high: 'text-orange-400 bg-orange-500/10',
  urgent: 'text-red-400 bg-red-500/10',
};

const statusColors: Record<string, string> = {
  pending: 'border-gray-500/30',
  in_progress: 'border-blue-500/30',
  completed: 'border-green-500/30',
  cancelled: 'border-red-500/30',
};

export default function TaskPanel() {
  const { tasks, isLoading, createTask, updateTask, deleteTask } = useTasks();
  const [newTitle, setNewTitle] = useState('');
  const [filter, setFilter] = useState<'all' | Task['status']>('all');

  const filteredTasks = tasks.filter((t) => filter === 'all' || t.status === filter);

  const handleCreate = () => {
    if (!newTitle.trim()) return;
    createTask({ title: newTitle.trim(), status: 'pending', priority: 'medium', tags: [] });
    setNewTitle('');
  };

  const toggleStatus = (task: Task) => {
    const next = task.status === 'completed' ? 'pending' : 'completed';
    updateTask({ id: task.id, status: next });
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {/* Add Task */}
      <div className="glass rounded-xl p-4">
        <div className="flex gap-2">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="Add a new task..."
            className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
          />
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-600"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-gray-500" />
        {(['all', 'pending', 'in_progress', 'completed'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              'rounded-full px-3 py-1 text-xs font-medium transition-all',
              filter === f ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-400 hover:bg-white/10',
            )}
          >
            {f === 'all' ? 'All' : f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="space-y-2">
        {filteredTasks.length === 0 ? (
          <div className="glass rounded-xl p-8 text-center">
            <p className="text-sm text-gray-500">No tasks found</p>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              className={clsx(
                'glass rounded-xl p-4 border-l-2 transition-all hover:bg-white/[0.07]',
                statusColors[task.status],
              )}
            >
              <div className="flex items-start gap-3">
                <button
                  onClick={() => toggleStatus(task)}
                  className={clsx(
                    'mt-0.5 h-5 w-5 rounded-full border-2 transition-all',
                    task.status === 'completed'
                      ? 'border-green-500 bg-green-500'
                      : 'border-gray-500 hover:border-blue-400',
                  )}
                >
                  {task.status === 'completed' && (
                    <svg className="h-full w-full text-white" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
                <div className="flex-1">
                  <p className={clsx(
                    'text-sm font-medium',
                    task.status === 'completed' ? 'text-gray-500 line-through' : 'text-white',
                  )}>
                    {task.title}
                  </p>
                  <div className="mt-2 flex items-center gap-3">
                    <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-medium uppercase', priorityColors[task.priority])}>
                      <Flag className="mr-1 inline h-3 w-3" />
                      {task.priority}
                    </span>
                    {task.dueDate && (
                      <span className="flex items-center gap-1 text-[10px] text-gray-500">
                        <Calendar className="h-3 w-3" />
                        {format(new Date(task.dueDate), 'MMM d')}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteTask(task.id)}
                  className="rounded p-1 text-gray-600 transition-colors hover:bg-red-500/10 hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
