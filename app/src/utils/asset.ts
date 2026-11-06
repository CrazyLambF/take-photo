/**
 * 静态资源路径解析。
 *
 * 为什么需要：图片路径在 poses.json 里存的是相对形式（`poses/ST-01/cover.jpg`），
 * 早期各处直接写成 `` `/${path}` ``，在根路径部署下没问题，但 GitHub Pages 项目
 * 站点跑在 `/<repo>/` 子路径下会全部 404。
 *
 * `import.meta.env.BASE_URL` 由 vite 的 `base` 决定，末尾自带 `/`，
 * 所以拼接时要把路径开头的 `/` 去掉，避免出现 `//`。
 */
const PLACEHOLDER = 'poses/placeholder.svg'

export function asset(path?: string | null): string {
  const clean = (path ?? '').replace(/^\/+/, '')
  return `${import.meta.env.BASE_URL}${clean || PLACEHOLDER}`
}

/** 缺少封面时的占位图 */
export function placeholder(): string {
  return `${import.meta.env.BASE_URL}${PLACEHOLDER}`
}
