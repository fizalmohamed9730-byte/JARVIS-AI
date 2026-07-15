import { useState, useEffect, useCallback } from 'react';
import { Search, Star, Mail, MailOpen, Send, Paperclip, ChevronLeft } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { api } from '@/utils/api';
import type { Email } from '@/types';

export default function EmailPanel() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [search, setSearch] = useState('');
  const [showCompose, setShowCompose] = useState(false);
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [accountId, setAccountId] = useState<number | null>(null);
  const [sending, setSending] = useState(false);

  const fetchAccounts = useCallback(async () => {
    try {
      const { data } = await api.get('/email/accounts');
      if (data.length > 0) setAccountId(data[0].id);
    } catch { /* ignore */ }
  }, []);

  const fetchInbox = useCallback(async () => {
    if (accountId === null) return;
    try {
      const { data } = await api.get('/email/inbox', { params: { account_id: accountId } });
      const mapped: Email[] = data.map((e: Record<string, unknown>) => {
        const sender = (e.sender as string) || '';
        const match = sender.match(/^(.*?)\s*<(.+?)>$/);
        return {
          id: String(e.id),
          from: match ? match[2] : sender,
          fromName: match ? match[1] : sender,
          to: [],
          subject: (e.subject as string) || '',
          body: (e.body as string) || '',
          snippet: ((e.body as string) || '').slice(0, 100),
          read: true,
          starred: false,
          category: 'primary' as const,
          date: (e.date as string) || new Date().toISOString(),
        };
      });
      setEmails(mapped);
    } catch {
      setEmails([]);
    }
  }, [accountId]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  useEffect(() => {
    fetchInbox();
  }, [fetchInbox]);

  const filtered = emails.filter((e) =>
    !search || e.subject.toLowerCase().includes(search.toLowerCase()) || e.fromName.toLowerCase().includes(search.toLowerCase()),
  );

  const unreadCount = emails.filter((e) => !e.read).length;

  if (selectedEmail) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="glass rounded-xl">
          <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
            <button onClick={() => setSelectedEmail(null)} className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-white">{selectedEmail.subject}</h3>
              <p className="text-xs text-gray-500">From: {selectedEmail.fromName} &lt;{selectedEmail.from}&gt;</p>
            </div>
          </div>
          <div className="p-6">
            <p className="text-sm leading-relaxed text-gray-300">{selectedEmail.body}</p>
          </div>
          <div className="border-t border-white/10 px-4 py-3">
            <button
              onClick={async () => {
                if (!selectedEmail || accountId === null) return;
                const replyBody = prompt('Enter your reply:');
                if (!replyBody) return;
                try {
                  await api.post(`/email/reply/${selectedEmail.id}`, {
                    to: [selectedEmail.from],
                    subject: selectedEmail.subject,
                    body: replyBody,
                  }, { params: { account_id: accountId } });
                  setSelectedEmail(null);
                } catch { /* ignore */ }
              }}
              className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600"
            >
              <Send className="h-4 w-4" /> Reply
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Inbox</h2>
          <p className="text-xs text-gray-500">{unreadCount} unread</p>
        </div>
        <button
          onClick={() => setShowCompose(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
        >
          <Mail className="h-4 w-4" />
          Compose
        </button>
      </div>

      <div className="glass rounded-xl p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search emails..."
            className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
          />
        </div>
      </div>

      <div className="space-y-1">
        {filtered.map((email) => (
          <button
            key={email.id}
            onClick={() => setSelectedEmail(email)}
            className={clsx(
              'glass w-full rounded-xl px-4 py-3 text-left transition-all hover:bg-white/[0.07]',
              !email.read && 'border-l-2 border-l-blue-500',
            )}
          >
            <div className="flex items-start gap-3">
              <div className="mt-1">
                {email.read ? (
                  <MailOpen className="h-4 w-4 text-gray-500" />
                ) : (
                  <Mail className="h-4 w-4 text-blue-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className={clsx('text-sm', !email.read ? 'font-medium text-white' : 'text-gray-300')}>
                    {email.fromName}
                  </span>
                  <div className="flex items-center gap-2">
                    {email.starred && <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />}
                    <span className="text-[10px] text-gray-600">{format(new Date(email.date), 'MMM d, HH:mm')}</span>
                  </div>
                </div>
                <p className={clsx('text-sm', !email.read ? 'font-medium text-gray-200' : 'text-gray-400')}>
                  {email.subject}
                </p>
                <p className="mt-1 truncate text-xs text-gray-500">{email.snippet}</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Compose Modal */}
      {showCompose && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="glass w-full max-w-lg rounded-2xl p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Compose Email</h3>
            <div className="space-y-3">
              <input value={composeTo} onChange={(e) => setComposeTo(e.target.value)} placeholder="To" className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50" />
              <input value={composeSubject} onChange={(e) => setComposeSubject(e.target.value)} placeholder="Subject" className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50" />
              <textarea value={composeBody} onChange={(e) => setComposeBody(e.target.value)} rows={6} placeholder="Write your email..." className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50" />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowCompose(false)} className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:bg-white/10">Cancel</button>
              <button
                disabled={sending}
                onClick={async () => {
                  if (!composeTo || !composeSubject || !composeBody) return;
                  setSending(true);
                  try {
                    await api.post('/email/send', {
                      to: composeTo.split(',').map((s: string) => s.trim()),
                      subject: composeSubject,
                      body: composeBody,
                      account_id: accountId,
                    });
                    setShowCompose(false);
                    setComposeTo('');
                    setComposeSubject('');
                    setComposeBody('');
                  } catch { /* ignore */ }
                  setSending(false);
                }}
                className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
              >
                <Send className="h-4 w-4" /> {sending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
