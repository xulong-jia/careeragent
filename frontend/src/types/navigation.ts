export type PageKey = "dashboard" | "resume" | "jd" | "match" | "knowledge";

export type NavigationItem = {
  key: PageKey;
  label: string;
  description: string;
};
