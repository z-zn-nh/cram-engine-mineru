import { FileText } from "lucide-react";
import type { ArtifactContent, ChatArtifact } from "../api/client";

type ArtifactPreviewProps = {
  artifact?: ChatArtifact;
  content?: ArtifactContent;
  isLoading: boolean;
};

export function ArtifactPreview({ artifact, content, isLoading }: ArtifactPreviewProps) {
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

      {!isLoading && content && <pre>{content.content}</pre>}

      {!isLoading && !content && (
        <p className="empty-state">这个产物还没有可预览内容，生成后会保存在当前学科文件夹。</p>
      )}
    </div>
  );
}
