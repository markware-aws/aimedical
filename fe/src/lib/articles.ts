import { getCollection, type CollectionEntry } from "astro:content";

export type Article = CollectionEntry<"articles">;

export async function getPublishedArticles(): Promise<Article[]> {
  const all = await getCollection("articles", ({ data }) => data.published === true);
  return all.sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

export async function getFeatured(): Promise<Article | undefined> {
  const all = await getPublishedArticles();
  return all.find((a) => a.data.featured) ?? all[0];
}

export async function getByCategory(category: string): Promise<Article[]> {
  const all = await getPublishedArticles();
  return all.filter((a) => a.data.category === category);
}

export async function getCategoryCounts(): Promise<Map<string, number>> {
  const all = await getPublishedArticles();
  const counts = new Map<string, number>();
  for (const article of all) {
    counts.set(article.data.category, (counts.get(article.data.category) ?? 0) + 1);
  }
  return counts;
}

export function tagSlug(tag: string): string {
  return tag
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export async function getTags(): Promise<{ tag: string; slug: string; count: number }[]> {
  const all = await getPublishedArticles();
  const counts = new Map<string, { tag: string; slug: string; count: number }>();

  for (const article of all) {
    for (const tag of article.data.tags) {
      const slug = tagSlug(tag);
      if (!slug) continue;
      const existing = counts.get(slug);
      if (existing) existing.count++;
      else counts.set(slug, { tag, slug, count: 1 });
    }
  }

  return [...counts.values()].sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}

export async function getByTag(slug: string): Promise<Article[]> {
  const all = await getPublishedArticles();
  return all.filter((article) => article.data.tags.some((tag) => tagSlug(tag) === slug));
}

export async function getRelated(article: Article, limit = 3): Promise<Article[]> {
  const all = await getPublishedArticles();
  return all
    .filter((a) => a.slug !== article.slug && a.data.category === article.data.category)
    .slice(0, limit);
}
