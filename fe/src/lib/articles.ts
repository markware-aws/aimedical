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

export async function getRelated(article: Article, limit = 3): Promise<Article[]> {
  const all = await getPublishedArticles();
  return all
    .filter((a) => a.slug !== article.slug && a.data.category === article.data.category)
    .slice(0, limit);
}
