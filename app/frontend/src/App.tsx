import { useEffect, useMemo, useState } from "react";
import { Bot, FileText, Upload } from "lucide-react";
import { createSubject, listSubjects, type SubjectSummary } from "./api/client";
import { SubjectSidebar } from "./components/SubjectSidebar";

const fallbackSubjects: SubjectSummary[] = [
  { name: "通信原理", slug: "通信原理" },
  { name: "数字电路", slug: "数字电路" },
  { name: "机器学习", slug: "机器学习" },
];

const citations = [
  {
    source: "教材.pdf",
    locator: "第 45 页",
    excerpt: "调制是把基带信号搬移到载波上的过程。",
  },
  {
    source: "第 3 讲.pptx",
    locator: "第 8 页",
    excerpt: "AM、FM、ASK、FSK、PSK 的对比。",
  },
];

const artifacts = ["期末速成路线.md", "通信原理总图.json", "调制解调练习题.md"];

export function App() {
  const [subjects, setSubjects] = useState<SubjectSummary[]>(fallbackSubjects);
  const [selectedSlug, setSelectedSlug] = useState(fallbackSubjects[0].slug);

  useEffect(() => {
    let isMounted = true;

    listSubjects()
      .then((loadedSubjects) => {
        if (!isMounted || loadedSubjects.length === 0) {
          return;
        }
        setSubjects(loadedSubjects);
        setSelectedSlug((current) =>
          loadedSubjects.some((subject) => subject.slug === current) ? current : loadedSubjects[0].slug,
        );
      })
      .catch(() => {
        // Keep the local preview subjects when the desktop backend is not running yet.
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const selectedSubject = useMemo(
    () => subjects.find((subject) => subject.slug === selectedSlug) ?? subjects[0],
    [selectedSlug, subjects],
  );

  async function handleCreateSubject() {
    const name = window.prompt("输入学科名称，例如：通信原理");
    if (!name?.trim()) {
      return;
    }

    const created = await createSubject(name.trim()).catch(() => ({
      name: name.trim(),
      slug: name.trim(),
    }));
    setSubjects((current) =>
      current.some((subject) => subject.slug === created.slug) ? current : [...current, created],
    );
    setSelectedSlug(created.slug);
  }

  return (
    <main className="shell">
      <SubjectSidebar
        subjects={subjects}
        selectedSlug={selectedSubject.slug}
        onCreateSubject={handleCreateSubject}
        onSelectSubject={setSelectedSlug}
      />

      <section className="chat-pane">
        <header className="chat-header">
          <div>
            <h1>{selectedSubject.name}</h1>
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
            <p>
              优先复习调制解调、傅里叶分析、信道噪声、抽样定理和数字调制。每个模块会附引用来源，生成的速成路线会保存到当前学科文件夹。
            </p>
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
                <div>
                  {citation.source} · {citation.locator}
                </div>
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
