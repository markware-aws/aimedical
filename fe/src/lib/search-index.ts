import { categoryLabel } from "../consts";
import { getPublishedArticles, getPublishedDate, type Article } from "./articles";

export type SearchIndexEntry = {
  title: string;
  description: string;
  category: string;
  categoryGr: string;
  date: string;
  url: string;
  searchText: string;
};

export function normalizeSearch(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ς/g, "σ");
}

export function buildSearchIndex(articles: Article[]): SearchIndexEntry[] {
  return articles.map((article) => {
    const { title, originalTitle, description, subtitle, category, tags, conditions } =
      article.data;
    const categoryGr = categoryLabel(category);
    const publishedDate = getPublishedDate(article);
    return {
      title,
      description: description || subtitle || "",
      category,
      categoryGr,
      date: publishedDate.toLocaleDateString("el-GR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      }),
      url: `/articles/${article.slug}/`,
      searchText: [title, originalTitle, description, subtitle, category, categoryGr, ...tags, ...(conditions ?? [])]
        .filter(Boolean)
        .join(" "),
    };
  });
}

export async function getSearchIndex(): Promise<SearchIndexEntry[]> {
  return buildSearchIndex(await getPublishedArticles());
}
