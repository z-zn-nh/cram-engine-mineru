export type MindMapNode = {
  id?: string;
  label: string;
  citations?: string[];
  children?: MindMapNode[];
};

export type MindMapDocument = {
  title: string;
  nodes: MindMapNode[];
};

type MindMapPreviewProps = {
  mindMap: MindMapDocument;
};

function MindMapBranch({ node }: { node: MindMapNode }) {
  return (
    <li>
      <div className="mindmap-node">
        <span>{node.label}</span>
        {node.citations && node.citations.length > 0 && (
          <small>{node.citations.slice(0, 3).join(" · ")}</small>
        )}
      </div>
      {node.children && node.children.length > 0 && (
        <ul>
          {node.children.map((child, index) => (
            <MindMapBranch key={child.id ?? `${child.label}-${index}`} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function MindMapPreview({ mindMap }: MindMapPreviewProps) {
  return (
    <div className="mindmap-preview">
      <strong>{mindMap.title}</strong>
      <ul>
        {mindMap.nodes.map((node, index) => (
          <MindMapBranch key={node.id ?? `${node.label}-${index}`} node={node} />
        ))}
      </ul>
    </div>
  );
}
