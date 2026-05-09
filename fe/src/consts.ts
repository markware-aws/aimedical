export const SITE_NAME = "AI Medical News Greece";
export const SITE_TAGLINE = "Ενημέρωση για την τεχνητή νοημοσύνη στην ιατρική";
export const SITE_URL = import.meta.env.SITE ?? "https://aimedical.gr";

export const CATEGORIES = [
  { slug: "oncology", labelGr: "Ογκολογία" },
  { slug: "cardiology", labelGr: "Καρδιολογία" },
  { slug: "neurology", labelGr: "Νευρολογία" },
  { slug: "hepatology", labelGr: "Ηπατολογία" },
  { slug: "immunology", labelGr: "Ανοσολογία" },
  { slug: "diagnostics", labelGr: "Διαγνωστική" },
  { slug: "radiology", labelGr: "Ακτινολογία" },
  { slug: "llms", labelGr: "Γλωσσικά μοντέλα" },
  { slug: "drug-discovery", labelGr: "Ανάπτυξη φαρμάκων" },
  { slug: "robotics", labelGr: "Ρομποτική" },
  { slug: "digital-health", labelGr: "Ψηφιακή υγεία" },
  { slug: "public-health", labelGr: "Δημόσια υγεία" },
  { slug: "women-health", labelGr: "Υγεία γυναικών" },
  { slug: "other", labelGr: "Άλλα" },
] as const;

export const PRIMARY_NAV_CATEGORIES = ["oncology", "cardiology", "neurology", "diagnostics", "radiology"] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];

export function categoryLabel(slug: string): string {
  return CATEGORIES.find((c) => c.slug === slug)?.labelGr ?? slug;
}
