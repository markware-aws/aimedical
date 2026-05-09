export const SITE_NAME = "AI Medical News Greece";
export const SITE_TAGLINE = "Ενημέρωση για την τεχνητή νοημοσύνη στην ιατρική";
export const SITE_URL = import.meta.env.SITE ?? "https://aimedical.gr";

export const CATEGORIES = [
  { slug: "oncology", labelGr: "Ογκολογία" },
  { slug: "diagnostics", labelGr: "Διαγνωστική" },
  { slug: "radiology", labelGr: "Ακτινολογία" },
  { slug: "llms", labelGr: "Γλωσσικά μοντέλα" },
  { slug: "drug-discovery", labelGr: "Ανάπτυξη φαρμάκων" },
  { slug: "robotics", labelGr: "Ρομποτική" },
  { slug: "other", labelGr: "Άλλα" },
] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];

export function categoryLabel(slug: string): string {
  return CATEGORIES.find((c) => c.slug === slug)?.labelGr ?? slug;
}
