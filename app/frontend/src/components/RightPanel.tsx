import { useEffect, useMemo, useState } from "react";
import { FileText } from "lucide-react";
import {
  listArtifacts,
  listCitations,
  readArtifactContent,
  type ArtifactContent,
  type ChatArtifact,
  type ChatCitation,
} from "../api/client";
import { ArtifactPreview } from "./ArtifactPreview";

type RightPanelProps = {
  latestArtifacts: ChatArtifact[];
  latestCitations: ChatCitation[];
  subjectSlug: string;
};

function artifactKey(artifact: ChatArtifact) {
  return artifact.relative_path ?? `${artifact.artifact_type}-${artifact.title}`;
}

function citationKey(citation: ChatCitation) {
  return citation.citation_label ?? `${citation.source_file}-${citation.locator}-${citation.chunk_id}`;
}

export function RightPanel({ latestArtifacts, latestCitations, subjectSlug }: RightPanelProps) {
  const [storedArtifacts, setStoredArtifacts] = useState<ChatArtifact[]>([]);
  const [storedCitations, setStoredCitations] = useState<ChatCitation[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<ChatArtifact | undefined>();
  const [preview, setPreview] = useState<ArtifactContent | undefined>();
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setSelectedArtifact(undefined);
    setPreview(undefined);

    Promise.all([listArtifacts(subjectSlug), listCitations(subjectSlug)])
      .then(([artifacts, citations]) => {
        if (!isMounted) {
          return;
        }
        setStoredArtifacts(artifacts);
        setStoredCitations(citations);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setStoredArtifacts([]);
        setStoredCitations([]);
      });

    return () => {
      isMounted = false;
    };
  }, [subjectSlug]);

  const artifacts = useMemo(() => {
    const byKey = new Map<string, ChatArtifact>();
    for (const artifact of [...storedArtifacts, ...latestArtifacts]) {
      byKey.set(artifactKey(artifact), artifact);
    }
    return Array.from(byKey.values());
  }, [latestArtifacts, storedArtifacts]);

  const citations = latestCitations.length > 0 ? latestCitations : storedCitations;

  async function handleSelectArtifact(artifact: ChatArtifact) {
    setSelectedArtifact(artifact);
    setPreview(undefined);
    if (!artifact.relative_path) {
      return;
    }

    setIsPreviewLoading(true);
    try {
      setPreview(await readArtifactContent(subjectSlug, artifact.relative_path));
    } catch {
      setPreview(undefined);
    } finally {
      setIsPreviewLoading(false);
    }
  }

  return (
    <aside className="result-pane">
      <section>
        <h2>引用资料</h2>
        <div className="stack">
          {citations.length === 0 && <p className="empty-state">资料中未找到明确出处。</p>}
          {citations.map((citation) => (
            <article className="citation" key={citationKey(citation)}>
              <div>
                {citation.source_file ?? "未知资料"} · {citation.locator ?? citation.citation_label ?? "未标注位置"}
              </div>
              {citation.excerpt && <p>{citation.excerpt}</p>}
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2>产出结果</h2>
        <div className="stack artifact-list">
          {artifacts.length === 0 && <p className="empty-state">当前学科还没有可展示产物。</p>}
          {artifacts.map((artifact) => {
            const isActive = artifactKey(artifact) === (selectedArtifact && artifactKey(selectedArtifact));
            return (
              <button
                className={isActive ? "artifact active" : "artifact"}
                key={artifactKey(artifact)}
                onClick={() => void handleSelectArtifact(artifact)}
                type="button"
              >
                <FileText size={15} />
                <span>{artifact.title}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <h2>产物预览</h2>
        <ArtifactPreview artifact={selectedArtifact} content={preview} isLoading={isPreviewLoading} />
      </section>
    </aside>
  );
}
