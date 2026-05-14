import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";
import tailwind from "@astrojs/tailwind";
import sitemap from "@astrojs/sitemap";

const SITE = process.env.SITE_URL ?? "https://aimedical.gr";

export default defineConfig({
  site: SITE,
  output: "static",
  trailingSlash: "always",
  integrations: [mdx(), tailwind(), sitemap()],
  build: { format: "directory" },
  vite: { ssr: { noExternal: ["@astrojs/rss"] } },
});
