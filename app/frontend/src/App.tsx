import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createSubject,
  healthCheck,
  listSubjects,
  type ChatArtifact,
  type ChatCitation,
  type SubjectSummary,
} from "./api/client";
import { ReviewChat } from "./components/ReviewChat";
import { RightPanel } from "./components/RightPanel";
import { SubjectSidebar } from "./components/SubjectSidebar";

const fallbackSubjects: SubjectSummary[] = [
  { name: "通信原理", slug: "通信原理" },
  { name: "数字电路", slug: "数字电路" },
  { name: "机器学习", slug: "机器学习" },
];

export function App() {
  const [subjects, setSubjects] = useState<SubjectSummary[]>(fallbackSubjects);
  const [selectedSlug, setSelectedSlug] = useState(fallbackSubjects[0].slug);
  const [latestCitations, setLatestCitations] = useState<ChatCitation[]>([]);
  const [latestArtifacts, setLatestArtifacts] = useState<ChatArtifact[]>([]);
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    let isMounted = true;

    healthCheck()
      .then((ok) => {
        if (isMounted) {
          setBackendReady(ok);
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendReady(false);
        }
      });

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

  return (
    <main className="shell">
      <SubjectSidebar
        backendReady={backendReady}
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

      <RightPanel
        latestArtifacts={latestArtifacts}
        latestCitations={latestCitations}
        subjectSlug={selectedSubject.slug}
      />
    </main>
  );
}
