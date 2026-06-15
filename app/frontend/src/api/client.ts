export type SubjectSummary = {
  name: string;
  slug: string;
};

export type ChatCitation = {
  chunk_id?: string;
  source_file?: string;
  locator?: string;
  citation_label?: string;
  excerpt?: string;
};

export type ChatArtifact = {
  artifact_type?: string;
  title: string;
  path?: string;
  relative_path?: string;
};

export type ChatResponse = {
  message: string;
  citations: ChatCitation[];
  artifacts: ChatArtifact[];
};

async function responseError(response: Response, fallback: string): Promise<Error> {
  const payload = await response.json().catch(() => undefined);
  const detail = typeof payload?.detail === "string" ? payload.detail : fallback;
  return new Error(detail);
}

export async function listSubjects(): Promise<SubjectSummary[]> {
  const response = await fetch("/subjects");
  if (!response.ok) {
    throw new Error("Failed to load subjects");
  }
  return response.json();
}

export async function sendChatMessage(subjectSlug: string, message: string): Promise<ChatResponse> {
  const response = await fetch(`/subjects/${encodeURIComponent(subjectSlug)}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw await responseError(response, "Failed to send chat message");
  }
  return response.json();
}

export async function createSubject(name: string): Promise<SubjectSummary> {
  const response = await fetch("/subjects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error("Failed to create subject");
  }
  return response.json();
}
