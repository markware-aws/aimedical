export const PAGE_SIZE = 24;

export function paginate<T>(items: T[], pageSize = PAGE_SIZE): T[][] {
  if (items.length === 0) return [[]];
  const pages: T[][] = [];
  for (let i = 0; i < items.length; i += pageSize) {
    pages.push(items.slice(i, i + pageSize));
  }
  return pages;
}

export function pageHref(basePath: string, page: number): string {
  if (page <= 1) return basePath;
  return `${basePath}${page}/`;
}

export function parsePageParam(value: string | undefined): number {
  if (!value) return 1;
  const page = Number.parseInt(value, 10);
  return Number.isFinite(page) && page > 0 ? page : 1;
}
