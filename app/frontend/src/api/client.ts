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

