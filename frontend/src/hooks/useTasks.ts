import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/utils/api';
import type { Task } from '@/types';
import toast from 'react-hot-toast';

export function useTasks() {
  const queryClient = useQueryClient();

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      const res = await api.get('/tasks');
      const list = res.data?.items || res.data || [];
      return list.map((t: Record<string, unknown>) => ({
        ...t,
        id: String(t.id),
        dueDate: t.due_date as string | undefined,
        createdAt: t.created_at as string,
        updatedAt: t.updated_at as string,
      })) as Task[];
    },
  });

  const createMutation = useMutation({
    mutationFn: (task: Partial<Task>) => api.post('/tasks', {
      title: task.title,
      description: task.description,
      priority: task.priority,
      due_date: task.dueDate,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task created');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: Partial<Task> & { id: string }) => api.patch(`/tasks/${id}`, {
      title: data.title,
      description: data.description,
      priority: data.priority,
      status: data.status,
      due_date: data.dueDate,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task updated');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/tasks/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task deleted');
    },
  });

  return {
    tasks,
    isLoading,
    createTask: createMutation.mutate,
    updateTask: updateMutation.mutate,
    deleteTask: deleteMutation.mutate,
  };
}
