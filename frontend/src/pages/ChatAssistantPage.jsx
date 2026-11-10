import { useEffect, useRef, useState } from "react";
import { Bot, Send, Sparkles, Trash2, User } from "lucide-react";
import { api } from "../api/client";
import { SimulatedBanner } from "../components/SimulatedBanner";

const SUGGESTED_PROMPTS = [
  "Why did TradeWise AI generate the latest prediction for AAPL?",
  "Summarize our prediction accuracy and accountability score",
  "What is the simulated market trend and risk for NVDA?",
  "What is RSI and how do beginners interpret it?",
  "How is my virtual portfolio performing?",
  "Can AI guarantee profits in trading?",
];

function FormattedMessage({ text }) {
  // Clean lightweight formatter for bold (**text**), headings (###), and bullet lists
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5 text-xs sm:text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith("### ")) {
          return (
            <h4 key={i} className="pt-1 font-bold text-slate-900 dark:text-white">
              {line.slice(4)}
            </h4>
          );
        }
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={i} className={line.startsWith("- ") ? "pl-3" : ""}>
            {parts.map((part, idx) =>
              part.startsWith("**") && part.endsWith("**") ? (
                <strong key={idx} className="font-semibold text-slate-900 dark:text-white">
                  {part.slice(2, -2)}
                </strong>
              ) : (
                part
              )
            )}
          </p>
        );
      })}
    </div>
  );
}

export function ChatAssistantPage() {
  const [messages, setMessages] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [contextSymbol, setContextSymbol] = useState("AAPL");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    Promise.all([api.getChatHistory(), api.getStocks()]).then(([hist, st]) => {
      setMessages(hist.messages || []);
      setStocks(st.stocks || []);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setSending(true);
    setInput("");
    try {
      const res = await api.sendChatMessage(trimmed, contextSymbol);
      setMessages((prev) => [...prev, res.user_message, res.assistant_message]);
    } finally {
      setSending(false);
    }
  };

  const handleClear = async () => {
    await api.clearChatHistory();
    setMessages([]);
  };

  return (
    <div className="flex h-[calc(100vh-8.5rem)] flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            AI Learning & Trading Chat Assistant
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Grounded in live SQLite simulated prices, ML prediction factors, and accountability metrics
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={contextSymbol}
            onChange={(e) => setContextSymbol(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
          >
            {stocks.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                Context: {s.symbol}
              </option>
            ))}
          </select>
          <button
            onClick={handleClear}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:text-rose-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </button>
        </div>
      </div>

      <SimulatedBanner compact />

      {/* Suggested prompts */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTED_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => sendMessage(p)}
            disabled={sending}
            className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-medium text-indigo-700 transition hover:bg-indigo-500/20 dark:text-indigo-300"
          >
            <Sparkles className="h-3 w-3" />
            {p}
          </button>
        ))}
      </div>

      {/* Chat feed */}
      <div className="fintech-card flex flex-1 flex-col overflow-hidden">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
              <Bot className="mb-2 h-10 w-10 text-indigo-500/70" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                Ask anything about simulated markets, AI predictions, or trading concepts!
              </p>
              <p className="mt-1 max-w-md text-xs">
                Click one of the prompt pills above or type your own question below.
              </p>
            </div>
          )}

          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "assistant" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-2xl px-4 py-3 ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "border border-slate-200/80 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-800/80 dark:text-slate-200"
                }`}
              >
                <FormattedMessage text={m.message} />
              </div>

              {m.role === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="flex items-center gap-2 border-t border-slate-200/80 p-3 dark:border-slate-800"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about market trends, RSI/MACD, prediction reasons, or accuracy history..."
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

