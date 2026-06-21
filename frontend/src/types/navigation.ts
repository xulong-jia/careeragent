export type PageKey = "dashboard" | "resume" | "jd" | "match";

export type NavigationItem = {
  key: PageKey;
  label: string;
  description: string;
};
