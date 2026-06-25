export type PageKey =
  | "dashboard"
  | "profile"
  | "resume"
  | "jd"
  | "match"
  | "project-optimization"
  | "interview"
  | "knowledge"
  | "agents"
  | "applications"
  | "evaluation"
  | "quality";

export type NavigationItem = {
  key: PageKey;
  label: string;
  description: string;
};
