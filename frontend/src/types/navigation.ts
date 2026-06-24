export type PageKey =
  | "dashboard"
  | "profile"
  | "resume"
  | "jd"
  | "match"
  | "project-optimization"
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
