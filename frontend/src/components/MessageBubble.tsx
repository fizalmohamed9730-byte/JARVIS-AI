import { useState } from 'react';
import { Copy, Check, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '@/types';
import { format } from 'date-fns';
import clsx from 'clsx';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={clsx('flex gap-3 animate-fade-in', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div
        className={clsx(
          'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full',
          isUser
            ? 'bg-gradient-to-br from-blue-500 to-blue-700'
            : 'bg-white/10',
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <span className="text-xs font-bold text-blue-400">J</span>
        )}
      </div>

      {/* Bubble */}
      <div className={clsx('max-w-[80%] space-y-1', isUser && 'text-right')}>
        <div
          className={clsx(
            'inline-block px-4 py-3 text-sm leading-relaxed',
            isUser ? 'chat-bubble-user text-white' : 'chat-bubble-assistant text-gray-200',
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <MarkdownContent content={message.content} />
          )}
        </div>
        <p className="px-1 text-[10px] text-gray-600">
          {format(new Date(message.timestamp), 'HH:mm')}
        </p>
      </div>
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      className="prose prose-invert prose-sm max-w-none"
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const codeStr = String(children).replace(/\n$/, '');

          if (match) {
            return <CodeBlock language={match[1]} code={codeStr} />;
          }
          return (
            <code className="rounded bg-white/10 px-1.5 py-0.5 text-blue-300" {...props}>
              {children}
            </code>
          );
        },
        p({ children }) {
          return <p className="mb-2 last:mb-0">{children}</p>;
        },
        ul({ children }) {
          return <ul className="mb-2 list-inside list-disc space-y-1">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="mb-2 list-inside list-decimal space-y-1">{children}</ol>;
        },
        h1({ children }) {
          return <h1 className="mb-2 text-lg font-bold text-white">{children}</h1>;
        },
        h2({ children }) {
          return <h2 className="mb-2 text-base font-semibold text-white">{children}</h2>;
        },
        h3({ children }) {
          return <h3 className="mb-1 text-sm font-semibold text-white">{children}</h3>;
        },
        a({ href, children }) {
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 underline hover:text-blue-300">
              {children}
            </a>
          );
        },
        blockquote({ children }) {
          return (
            <blockquote className="border-l-2 border-blue-500/50 pl-3 text-gray-400 italic">
              {children}
            </blockquote>
          );
        },
        table({ children }) {
          return (
            <div className="my-2 overflow-x-auto rounded-lg border border-white/10">
              <table className="w-full text-sm">{children}</table>
            </div>
          );
        },
        th({ children }) {
          return <th className="border-b border-white/10 bg-white/5 px-3 py-2 text-left font-medium">{children}</th>;
        },
        td({ children }) {
          return <td className="border-b border-white/5 px-3 py-2">{children}</td>;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-white/10">
      <div className="flex items-center justify-between bg-white/5 px-3 py-1.5">
        <span className="text-xs text-gray-400">{language}</span>
        <button
          onClick={handleCopy}
          className="rounded p-1 text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          background: 'rgba(0,0,0,0.3)',
          fontSize: '0.8rem',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
