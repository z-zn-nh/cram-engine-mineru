import {
  BookOpen,
  FileText,
  Folder,
  GitBranch,
  GraduationCap,
  ListChecks,
  NotebookPen,
  Plus,
  XCircle,
} from "lucide-react";

export type Subject = {
  name: string;
  slug: string;
};

type SubjectSidebarProps = {
  subjects: Subject[];
  selectedSlug: string;
  onCreateSubject: () => void;
  onSelectSubject: (slug: string) => void;
};

const groups = [
  { label: "资料", icon: FileText },
  { label: "速成计划", icon: GraduationCap },
  { label: "笔记", icon: NotebookPen },
  { label: "思维导图", icon: GitBranch },
  { label: "题库", icon: ListChecks },
  { label: "错题本", icon: XCircle },
  { label: "考前总结", icon: BookOpen },
];

export function SubjectSidebar({
  subjects,
  selectedSlug,
  onCreateSubject,
  onSelectSubject,
}: SubjectSidebarProps) {
  return (
    <aside className="subject-pane">
      <div className="brand">
        <BookOpen size={20} />
        <span>期末速成</span>
      </div>

      <button className="new-subject" type="button" onClick={onCreateSubject}>
        <Plus size={15} />
        新建学科
      </button>

      <nav className="subject-list" aria-label="学科文件夹">
        {subjects.map((subject) => {
          const isActive = subject.slug === selectedSlug;
          return (
            <section className={isActive ? "subject active" : "subject"} key={subject.slug}>
              <button className="subject-title" type="button" onClick={() => onSelectSubject(subject.slug)}>
                <Folder size={16} />
                <span>{subject.name}</span>
              </button>

              {isActive && (
                <div className="group-list">
                  {groups.map(({ label, icon: Icon }) => (
                    <button className="group-item" key={label} type="button">
                      <Icon size={14} />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </nav>
    </aside>
  );
}
