# 部署

`site/` 是可直接托管的纯静态站点，无构建步骤。

## GitHub Pages（已备好 workflow）

仓库根部已有 `.github/workflows/pages.yml`，推送到 `main` 且 `site/` 有变更时自动部署。

**首次需要仓库 Owner 手动启用一次**（我没有替你改仓库设置）：

1. 打开 `Settings → Pages`
2. `Source` 选 **GitHub Actions**
3. 回到 `Actions` 页手动跑一次 `Deploy site to GitHub Pages`

之后地址形如 `https://richardhu8.github.io/FengShui-Energy-Field/`。

## Cloudflare Pages（国内访问更稳，推荐）

```
Framework preset : None
Build command    : （留空）
Build output dir : 玄空飞星/site
```

连上 GitHub 仓库即可，每次推送自动部署。

## 本地预览

```bash
cd 玄空飞星/site && python3 -m http.server 8000
```

## 接上 AI 后端

部署好 `api/` 里的 Worker 后，在 `paipan.html` 的第一个 `<script>` 之前插入：

```html
<script>window.FENGSHUI_AI_ENDPOINT="https://fengshui-ai.你的账号.workers.dev";</script>
```

并把 Worker 的 `ALLOW_ORIGIN` 改成你的站点域名。

## 文件名说明

站点内用英文路径（`paipan.html` 等），避免 URL 出现 `%E7%8E%84%E7%A9%BA…` 转义串；
仓库源文件仍保留中文名。要改回中文路径，重命名后同步改 `index.html`
与两个工具页里的互链即可。
