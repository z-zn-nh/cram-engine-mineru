import { FileText } from "lucide-react";
import type { ArtifactContent, ChatArtifact } from "../api/client";
import { MindMapPreview, type MindMapDocument } from "./MindMapPreview";

type ArtifactPreviewProps = {
  artifact?: ChatArtifact;
  content?: ArtifactContent;
  isLoading: boolean;
};

export function ArtifactPreview({ artifact, content, isLoading }: ArtifactPreviewProps) {
  const mindMap = artifact?.artifact_type === "mindmap" && content ? parseMindMap(content.content) : undefined;

  if (!artifact) {
    return (
      <div className="artifact-preview empty-state">
        <FileText size={17} />
        <span>选择一个产出结果查看内容</span>
      </div>
    );
  }

  return (
    <div className="artifact-preview">
      <div className="artifact-preview-header">
        <FileText size={17} />
        <div>
          <strong>{artifact.title}</strong>
          {artifact.relative_path && <span>{artifact.relative_path}</span>}
        </div>
      </div>

      {isLoading && <p className="empty-state">正在读取产物内容...</p>}

      {!isLoading && mindMap && <MindMapPreview mindMap={mindMap} />}

      {!isLoading && content && !mindMap && <pre>{content.content}</pre>}

      {!isLoading && !content && (
        <p className="empty-state">这个产物还没有可预览内容，生成后会保存在当前学科文件夹。</p>
      )}
    </div>
  );
}

function parseMindMap(content: string): MindMapDocument | undefined {
  try {
    const payload = JSON.parse(content);
    if (!payload || typeof payload.title !== "string" || !Array.isArray(payload.nodes)) {
      return undefined;
    }
    return payload as MindMapDocument;
  } catch {
    return undefined;
  }
}
