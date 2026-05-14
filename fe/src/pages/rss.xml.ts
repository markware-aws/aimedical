import rss from "@astrojs/rss";
import type { APIContext } from "astro";
import { getPublishedArticles } from "../lib/articles";
import { SITE_NAME, SITE_TAGLINE } from "../consts";

export async function GET(context: APIContext) {
  const articles = await getPublishedArticles();
  return rss({
    title: SITE_NAME,
    description: SITE_TAGLINE,
    site: context.site ?? "https://aimedical.gr",
    items: articles.map((a) => ({
      title: a.data.title,
      description: a.data.description,
      pubDate: a.data.date,
      link: `/articles/${a.slug}/`,
      categories: [a.data.category, ...a.data.tags],
    })),
    customData: `<language>el-GR</language>`,
  });
}
