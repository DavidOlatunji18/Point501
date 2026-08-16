import { useState, type FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import { useTeams } from "../context/TeamsContext";
import { useChat } from "../context/ChatContext";
import { api } from "../lib/api";
import TeamSelector from "../components/TeamSelector";

const markdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="mb-2 list-disc pl-5 last:mb-0">{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className="mb-2 list-decimal pl-5 last:mb-0">{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => <li className="mb-0.5">{children}</li>,
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-semibold">{children}</strong>
  ),
};

export default function ChatPage() {
  const { selectedTeamId } = useTeams();
  const { messages, setMessages } = useChat();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setSending(true);

    try {
      const response = await api.chat(message, selectedTeamId ?? undefined);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, sources: response.sources },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "Something went wrong.",
          isError: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-extrabold text-gold">Chat</h1>
        <div className="flex items-center gap-3">
          <TeamSelector allowNone />
          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="rounded-md border border-outline px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-panel-alt"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-outline bg-panel p-4">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            Ask about start/sit decisions, waivers, trades, or general strategy. If a team is
            selected above, your roster is automatically included as context.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm ${
                msg.role === "user"
                  ? "bg-brand text-white whitespace-pre-wrap"
                  : msg.isError
                    ? "bg-red-950/40 text-red-300 whitespace-pre-wrap"
                    : "bg-panel-alt text-slate-100"
              }`}
            >
              {msg.role === "assistant" && !msg.isError ? (
                <ReactMarkdown components={markdownComponents}>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 border-t border-outline pt-2 text-xs text-slate-400">
                  <p className="font-medium">Sources:</p>
                  <ul className="list-inside list-disc">
                    {msg.sources.map((s, j) => (
                      <li key={j}>{s.title}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        {sending && <p className="text-sm text-slate-400">Thinking…</p>}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Should I start X or Y this week?"
          className="flex-1 rounded-md border border-outline bg-panel-alt px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-gold focus:outline-none"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
