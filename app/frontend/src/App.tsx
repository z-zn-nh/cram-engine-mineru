import { BookOpen, Bot, FileText, Folder, GitBranch, GraduationCap, ListChecks, NotebookPen, Upload } from "lucide-react";

const subjects = ["通信原理", "数字电路", "机器学习"];

const groups = [
  { label: "资料", icon: FileText },
  { label: "速成计划", icon: GraduationCap },
  { label: "笔记", icon: NotebookPen },
  { label: "思维导图", icon: GitBranch },
  { label: "题库", icon: ListChecks },
];

const citations = [
  { source: "教材.pdf", locator: "第 45 页", excerpt: "调制是把基带信号搬移到载波上的过程。" },
  { source: "第3讲.pptx", locator: "第 8 页", excerpt: "AM、FM、ASK、FSK、PSK 的对比。" },
];

const artifacts = ["期末速成路线.md", "通信原理总图.json", "调制解调练习题.md"];

export function App() {
  return (
    <main className="shell">
      <aside className="subject-pane">
        <div className="brand">
          <BookOpen size={20} />
          <span>期末速成</span>
        </div>
        <button className="new-subject" type="button">+ 新建学科</button>
        <nav className="subject-list" aria-label="学科文件夹">
          {subjects.map((subject, index) => (
            <section className={index === 0 ? "subject active" : "subject"} key={subject}>
              <div className="subject-title">
                <Folder size={16} />
                <span>{subject}</span>
              </div>
              {index === 0 && (
                <div className="group-list">
                  {groups.map(({ label, icon: Icon }) => (
                    <button className="group-item" key={label} type="button">
                      <Icon size={14} />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          ))}
        </nav>
      </aside>

      <section className="chat-pane">
        <header className="chat-header">
          <div>
            <h1>通信原理</h1>
            <p>对话式复习 · 基于资料引用 · 产物自动归档</p>
          </div>
          <button className="upload-button" type="button">
            <Upload size={16} />
            上传资料
          </button>
        </header>

        <div className="messages">
          <article className="message user">帮我根据这些 PPT 生成期末速成路线。</article>
          <article className="message assistant">
            <div className="assistant-title">
              <Bot size={16} />
              <span>已根据资料拆出 5 个核心模块</span>
            </div>
            <p>优先复习调制解调、傅里叶分析、信道噪声、抽样定理和数字调制。每个模块会附引用来源，生成的速成路线会保存到当前学科文件夹。</p>
          </article>
        </div>

        <form className="composer">
          <input aria-label="复习输入" placeholder="继续提问、让它讲解、出题或生成思维导图..." />
          <button type="button">发送</button>
        </form>
      </section>

      <aside className="result-pane">
        <section>
          <h2>引用资料</h2>
          <div className="stack">
            {citations.map((citation) => (
              <article className="citation" key={`${citation.source}-${citation.locator}`}>
                <div>{citation.source} · {citation.locator}</div>
                <p>{citation.excerpt}</p>
              </article>
            ))}
          </div>
        </section>

        <section>
          <h2>产出结果</h2>
          <div className="stack">
            {artifacts.map((artifact) => (
              <button className="artifact" key={artifact} type="button">
                <FileText size={15} />
                <span>{artifact}</span>
              </button>
            ))}
          </div>
        </section>
      </aside>
    </main>
  );
}

