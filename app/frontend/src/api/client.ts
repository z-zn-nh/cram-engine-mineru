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

export type ArtifactContent = {
  title: string;
  relative_path: string;
  content: string;
};

export type ChatResponse = {
  message: string;
  citations: ChatCitation[];
  artifacts: ChatArtifact[];
};

const API_BASE_URL = import.meta.env.VITE_CRAM_BACKEND_URL ?? "http://127.0.0.1:8000";

function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  const payload = await response.json().catch(() => undefined);
  const detail = typeof payload?.detail === "string" ? payload.detail : fallback;
  return new Error(detail);
}

export async function healthCheck(): Promise<boolean> {
  const response = await fetch(apiUrl("/health"));
  return response.ok;
}

export async function listSubjects(): Promise<SubjectSummary[]> {
  const response = await fetch(apiUrl("/subjects"));
  if (!response.ok) {
    throw new Error("Failed to load subjects");
  }
  return response.json();
}

export async function sendChatMessage(subjectSlug: string, message: string): Promise<ChatResponse> {
  const response = await fetch(apiUrl(`/subjects/${encodeURIComponent(subjectSlug)}/chat`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw await responseError(response, "Failed to send chat message");
  }
  return response.json();
}

export async function listArtifacts(subjectSlug: string): Promise<ChatArtifact[]> {
  const response = await fetch(apiUrl(`/subjects/${encodeURIComponent(subjectSlug)}/artifacts`));
  if (!response.ok) {
    throw await responseError(response, "Failed to load artifacts");
  }
  return response.json();
}

export async function listCitations(subjectSlug: string): Promise<ChatCitation[]> {
  const response = await fetch(apiUrl(`/subjects/${encodeURIComponent(subjectSlug)}/citations`));
  if (!response.ok) {
    throw await responseError(response, "Failed to load citations");
  }
  return response.json();
}

export async function readArtifactContent(subjectSlug: string, relativePath: string): Promise<ArtifactContent> {
  const params = new URLSearchParams({ relative_path: relativePath });
  const response = await fetch(apiUrl(`/subjects/${encodeURIComponent(subjectSlug)}/artifacts/content?${params}`));
  if (!response.ok) {
    throw await responseError(response, "Failed to read artifact");
  }
  return response.json();
}

export async function createSubject(name: string): Promise<SubjectSummary> {
  const response = await fetch(apiUrl("/subjects"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error("Failed to create subject");
  }
  return response.json();
}
