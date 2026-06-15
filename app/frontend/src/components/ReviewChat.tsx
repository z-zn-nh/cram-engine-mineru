import { FormEvent, useEffect, useMemo, useState } from "react";
import { Bot, Loader2, Send, Upload, User } from "lucide-react";
import { sendChatMessage, type ChatArtifact, type ChatCitation } from "../api/client";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: ChatCitation[];
};

type ReviewChatProps = {
  subjectName: string;
  subjectSlug: string;
  onChatResult: (result: { citations: ChatCitation[]; artifacts: ChatArtifact[] }) => void;
};

function messageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ReviewChat({ subjectName, subjectSlug, onChatResult }: ReviewChatProps) {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const welcomeMessage = useMemo<ChatMessage>(
    () => ({
      id: `welcome-${subjectSlug}`,
      role: "assistant",
      content: `已进入「${subjectName}」。可以直接问我梳理考点、讲概念、出题，或生成速成计划和思维导图。`,
    }),
    [subjectName, subjectSlug],
  );

  useEffect(() => {
    setMessages([welcomeMessage]);
    onChatResult({ citations: [], artifacts: [] });
  }, [onChatResult, welcomeMessage]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);
    setMessages((current) => [...current, { id: messageId(), role: "user", content: message }]);

    try {
      const response = await sendChatMessage(subjectSlug, message);
      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: "assistant",
          content: response.message,
          citations: response.citations,
        },
      ]);
      onChatResult({ citations: response.citations, artifacts: response.artifacts });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "发送失败";
      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: "assistant",
          content: `暂时不能调用模型：${detail}。请先配置 OpenAI-compatible API 后再继续。`,
        },
      ]);
      onChatResult({ citations: [], artifacts: [] });
    } finally {
      setIsSending(false);
    }
  }

  return (
    <>
      <header className="chat-header">
        <div>
          <h1>{subjectName}</h1>
          <p>对话式复习 · 基于资料引用 · 产物自动归档</p>
        </div>
        <div className="chat-actions">
          <span className="model-pill">OpenAI-compatible</span>
          <button className="upload-button" type="button">
            <Upload size={16} />
            上传资料
          </button>
        </div>
      </header>

      <div className="messages">
        {messages.map((message) => (
          <article className={`message ${message.role}`} key={message.id}>
            <div className="message-title">
              {message.role === "assistant" ? <Bot size={16} /> : <User size={16} />}
              <span>{message.role === "assistant" ? "速成引擎" : "我"}</span>
            </div>
            <p>{message.content}</p>
            {message.citations && message.citations.length > 0 && (
              <div className="inline-citations">
                {message.citations.slice(0, 3).map((citation) => (
                  <span key={citation.citation_label ?? citation.chunk_id}>
                    {citation.citation_label ?? citation.source_file}
                  </span>
                ))}
              </div>
            )}
          </article>
        ))}
        {isSending && (
          <article className="message assistant pending">
            <div className="message-title">
              <Loader2 className="spin" size={16} />
              <span>正在检索资料并生成回答</span>
            </div>
          </article>
        )}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <input
          aria-label="复习输入"
          onChange={(event) => setInput(event.target.value)}
          placeholder="继续提问、让它讲解、出题或生成思维导图..."
          value={input}
        />
        <button disabled={isSending || !input.trim()} type="submit">
          <Send size={15} />
          发送
        </button>
      </form>
    </>
  );
}
