export type SubjectSummary = {
  name: string;
  slug: string;
};

export async function listSubjects(): Promise<SubjectSummary[]> {
  const response = await fetch("/subjects");
  if (!response.ok) {
    throw new Error("Failed to load subjects");
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
