export type PageKey =
  | "dashboard"
  | "resume"
  | "jd"
  | "match"
  | "knowledge"
  | "agents"
  | "quality";

export type NavigationItem = {
  key: PageKey;
  label: string;
  description: string;
};
