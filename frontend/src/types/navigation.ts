export type PageKey =
  | "dashboard"
  | "profile"
  | "resume"
  | "jd"
  | "match"
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
