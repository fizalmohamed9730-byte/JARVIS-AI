import { useState, useEffect, useCallback } from 'react';
import { Zap, Play, Pause, Activity, BarChart3, Cpu, HardDrive } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { ActionLog } from '@/types';

const QUICK_ACTIONS = [
  { label: 'Open Notepad', command: 'notepad' },
  { label: 'System Info', command: 'systeminfo' },
  { label: 'List Processes', command: 'tasklist /FO CSV /NH | head -10' },
  { label: 'Check Network', command: 'ipconfig' },
];

export default function AutomationPanel() {
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({});
  const [platform, setPlatform] = useState('');
  const [logs, setLogs] = useState<ActionLog[]>([]);
  const [sysStats, setSysStats] = useState({ cpu: '--', memory: '--', uptime: '--' });
  const [executing, setExecuting] = useState<string | null>(null);

  const fetchCapabilities = useCallback(async () => {
    try {
      const { data } = await api.get('/automation/capabilities');
      setCapabilities(data.capabilities || {});
      setPlatform(data.platform || '');
    } catch { /* ignore */ }
  }, []);

  const fetchSystemStats = useCallback(async () => {
    try {
      const [cpuRes, memRes, uptimeRes] = await Promise.allSettled([
        api.post('/automation/system/command', { command: 'wmic cpu get loadpercentage /value' }),
        api.post('/automation/system/command', { command: 'wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value' }),
        api.post('/automation/system/command', { command: 'wmic os get lastbootuptime /value' }),
      ]);
      const stats = { cpu: '--', memory: '--', uptime: '--' };
      if (cpuRes.status === 'fulfilled' && cpuRes.value.data.success) {
        const m = cpuRes.value.data.message.match(/LoadPercentage=(\d+)/);
        if (m) stats.cpu = `${m[1]}%`;
      }
      if (memRes.status === 'fulfilled' && memRes.value.data.success) {
        const msg = memRes.value.data.message;
        const freeM = msg.match(/FreePhysicalMemory=(\d+)/);
        const totalM = msg.match(/TotalVisibleMemorySize=(\d+)/);
        if (freeM && totalM) {
          const freeGB = (parseInt(freeM[1]) / 1048576).toFixed(1);
          stats.memory = `${freeGB} GB free`;
        }
      }
      if (uptimeRes.status === 'fulfilled' && uptimeRes.value.data.success) {
        stats.uptime = 'Online';
      }
      setSysStats(stats);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchCapabilities();
    fetchSystemStats();
    const interval = setInterval(fetchSystemStats, 30000);
    return () => clearInterval(interval);
  }, [fetchCapabilities, fetchSystemStats]);

  const executeAction = useCallback(async (label: string, command: string) => {
    setExecuting(label);
    try {
      const { data } = await api.post('/automation/execute', { command });
      setLogs((prev) => [
        { id: Date.now().toString(), type: command, status: (data.success ? 'success' : 'failure') as 'success' | 'failure', details: `${label}: ${data.message}`, timestamp: new Date().toISOString() },
        ...prev,
      ].slice(0, 20));
    } catch (err) {
      setLogs((prev) => [
        { id: Date.now().toString(), type: command, status: 'failure' as 'failure', details: `${label}: Request failed`, timestamp: new Date().toISOString() },
        ...prev,
      ].slice(0, 20));
    }
    setExecuting(null);
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Quick Actions */}
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-500">Quick Actions</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => executeAction(action.label, action.command)}
              disabled={executing === action.label}
              className="glass rounded-xl p-4 text-center transition-all hover:bg-white/[0.07] disabled:opacity-50"
            >
              <Zap className="mx-auto mb-2 h-5 w-5 text-blue-400" />
              <span className="text-xs font-medium text-gray-300">{executing === action.label ? 'Running...' : action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* System Stats */}
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-500">System Status</h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: Cpu, label: 'CPU', value: sysStats.cpu },
            { icon: HardDrive, label: 'Memory', value: sysStats.memory },
            { icon: Activity, label: 'Status', value: sysStats.uptime },
          ].map((stat) => (
            <div key={stat.label} className="glass rounded-xl p-3">
              <div className="flex items-center gap-2">
                <stat.icon className="h-4 w-4 text-blue-400" />
                <span className="text-xs text-gray-500">{stat.label}</span>
              </div>
              <p className="mt-1 text-lg font-semibold text-white">{stat.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Capabilities Grid */}
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-500">Capabilities {platform && `(${platform})`}</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(capabilities).map(([key, enabled]) => (
            <div key={key} className="glass rounded-xl p-4 transition-all hover:bg-white/[0.07]">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-medium text-white">{key.replace(/_/g, ' ')}</h4>
                </div>
                <button className={clsx('rounded-full p-1.5', enabled ? 'bg-green-500/15 text-green-400' : 'bg-white/5 text-gray-500')}>
                  {enabled ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity Log */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-gray-500">
          <BarChart3 className="h-3 w-3" />
          Recent Activity
        </h3>
        <div className="glass rounded-xl divide-y divide-white/5">
          {logs.length === 0 ? (
            <div className="px-4 py-3 text-xs text-gray-500">No recent activity</div>
          ) : logs.map((log) => (
            <div key={log.id} className="flex items-center gap-3 px-4 py-3">
              <div className={clsx('h-2 w-2 rounded-full', log.status === 'success' ? 'bg-green-400' : log.status === 'failure' ? 'bg-red-400' : 'bg-yellow-400')} />
              <span className="flex-1 text-sm text-gray-300">{log.details}</span>
              <span className="text-[10px] text-gray-600">{format(new Date(log.timestamp), 'HH:mm')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
