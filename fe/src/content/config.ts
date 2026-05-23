import { defineCollection, z } from "astro:content";

const articles = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    originalTitle: z.string().optional(),
    subtitle: z.string().optional(),
    date: z.coerce.date(),
    publishedAt: z.coerce.date().optional(),
    description: z.string().default(""),
    category: z.enum([
      "oncology",
      "cardiology",
      "neurology",
      "hepatology",
      "immunology",
      "diagnostics",
      "radiology",
      "llms",
      "drug-discovery",
      "robotics",
      "digital-health",
      "public-health",
      "women-health",
      "other",
    ]),
    tags: z.array(z.string()).default([]),
    heroImage: z.string().optional(),
    sourceUrl: z.string().url(),
    doi: z.string().optional(),
    source: z.enum(["pubmed", "arxiv", "rss", "fda"]).optional(),
    conditions: z.array(z.string()).optional(),
    keyFindings: z.array(z.string()).optional(),
    studyLimitations: z.string().optional(),
    clinicalSignificance: z.string().optional(),
    published: z.boolean().default(false),
    generated: z.boolean().default(true),
    featured: z.boolean().default(false),
  }),
});

export const collections = { articles };
