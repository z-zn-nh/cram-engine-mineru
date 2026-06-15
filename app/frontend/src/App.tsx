import { useCallback, useEffect, useMemo, useState } from "react";
import { FileText } from "lucide-react";
import { createSubject, listSubjects, type ChatArtifact, type ChatCitation, type SubjectSummary } from "./api/client";
import { ReviewChat } from "./components/ReviewChat";
import { SubjectSidebar } from "./components/SubjectSidebar";

const fallbackSubjects: SubjectSummary[] = [
  { name: "通信原理", slug: "通信原理" },
  { name: "数字电路", slug: "数字电路" },
  { name: "机器学习", slug: "机器学习" },
];

const fallbackCitations: ChatCitation[] = [
  {
    source_file: "教材.pdf",
    locator: "第 45 页",
    citation_label: "教材.pdf:第45页",
    excerpt: "调制是把基带信号搬移到载波上的过程。",
  },
  {
    source_file: "第 3 讲.pptx",
    locator: "第 8 页",
    citation_label: "第3讲.pptx:第8页",
    excerpt: "AM、FM、ASK、FSK、PSK 的对比。",
  },
];

const fallbackArtifacts: ChatArtifact[] = [
  { title: "期末速成路线.md", artifact_type: "cram_plan" },
  { title: "通信原理总图.json", artifact_type: "mindmap" },
  { title: "调制解调练习题.md", artifact_type: "qbank" },
];

export function App() {
  const [subjects, setSubjects] = useState<SubjectSummary[]>(fallbackSubjects);
  const [selectedSlug, setSelectedSlug] = useState(fallbackSubjects[0].slug);
  const [latestCitations, setLatestCitations] = useState<ChatCitation[]>([]);
  const [latestArtifacts, setLatestArtifacts] = useState<ChatArtifact[]>([]);

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

  const handleChatResult = useCallback(
    (result: { citations: ChatCitation[]; artifacts: ChatArtifact[] }) => {
      setLatestCitations(result.citations);
      setLatestArtifacts(result.artifacts);
    },
    [],
  );

  const visibleCitations = latestCitations.length > 0 ? latestCitations : fallbackCitations;
  const visibleArtifacts = latestArtifacts.length > 0 ? latestArtifacts : fallbackArtifacts;

  return (
    <main className="shell">
      <SubjectSidebar
        subjects={subjects}
        selectedSlug={selectedSubject.slug}
        onCreateSubject={handleCreateSubject}
        onSelectSubject={setSelectedSlug}
      />

      <section className="chat-pane">
        <ReviewChat
          subjectName={selectedSubject.name}
          subjectSlug={selectedSubject.slug}
          onChatResult={handleChatResult}
        />
      </section>

      <aside className="result-pane">
        <section>
          <h2>引用资料</h2>
          <div className="stack">
            {visibleCitations.map((citation) => (
              <article className="citation" key={`${citation.source_file}-${citation.locator}-${citation.chunk_id}`}>
                <div>
                  {citation.source_file} · {citation.locator}
                </div>
                <p>{citation.excerpt}</p>
              </article>
            ))}
          </div>
        </section>

        <section>
          <h2>产出结果</h2>
          <div className="stack">
            {visibleArtifacts.map((artifact) => (
              <button className="artifact" key={`${artifact.artifact_type}-${artifact.title}`} type="button">
                <FileText size={15} />
                <span>{artifact.title}</span>
              </button>
            ))}
          </div>
        </section>
      </aside>
    </main>
  );
}
