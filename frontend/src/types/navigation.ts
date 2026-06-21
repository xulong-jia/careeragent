export type PageKey =
  | "dashboard"
  | "resume"
  | "jd"
  | "match"
  | "knowledge"
  | "agents";

export type NavigationItem = {
  key: PageKey;
  label: string;
  description: string;
};
