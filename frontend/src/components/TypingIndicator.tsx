export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10">
        <span className="text-xs font-bold text-blue-400">J</span>
      </div>
      <div className="chat-bubble-assistant px-4 py-3">
        <div className="flex items-center gap-1.5">
          <div className="typing-dot h-2 w-2 rounded-full bg-blue-400" />
          <div className="typing-dot h-2 w-2 rounded-full bg-blue-400" />
          <div className="typing-dot h-2 w-2 rounded-full bg-blue-400" />
        </div>
      </div>
    </div>
  );
}
