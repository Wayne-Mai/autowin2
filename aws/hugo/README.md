# Marketing Blogs · Hugo source

伪装站源码,用作 VPN VPS 的默认首页。设计目标:**域名打开就是个像样的市场营销博客**,挡住所有"这是个代理服务"的怀疑。

## 技术栈

| 组件 | 版本/选型 |
|---|---|
| Hugo | v0.145+(本机 `/usr/local/Homebrew/Cellar/hugo/0.145.0/bin/hugo`) |
| 主题 | [PaperMod](https://github.com/adityatelange/hugo-PaperMod)(git clone 到 `themes/PaperMod`) |
| 内容 | 6 篇市场营销博文(SEO / 内容 / 邮件 / 归因 / 品牌 / MQL) |

## 目录结构

```
hugo/
├── hugo.toml              # 站点配置(站名、菜单、主题参数)
├── content/posts/         # 博文 markdown
├── themes/PaperMod/       # 主题(独立 git clone,不是 submodule)
├── archetypes/            # 新文章模板(空,用默认)
├── static/                # 静态资源(空)
└── public/                # 构建输出(gitignore 候选)
```

## 构建

```bash
cd /Users/wayne/Documents/Trade/aws/hugo
/usr/local/Homebrew/Cellar/hugo/0.145.0/bin/hugo --minify
# 或直接:
hugo --minify    # 如果 PATH 里有 hugo
```

产物在 `public/` 下。

## 部署到 VPS

```bash
HUGO_DIR=/Users/wayne/Documents/Trade/aws/hugo
KEY=/Users/wayne/Documents/Trade/aws/LightsailDefaultKey-ap-southeast-2.pem
VPS=ubuntu@52.64.70.157

# 1. 构建
cd "$HUGO_DIR" && /usr/local/Homebrew/Cellar/hugo/0.145.0/bin/hugo --minify

# 2. 推到 VPS 临时目录(rsync 经 ssh,无需 root)
rsync -avz --delete -e "ssh -i $KEY" public/ $VPS:/tmp/site/

# 3. 移到 nginx 服务目录
ssh -i $KEY $VPS 'sudo rsync -a --delete /tmp/site/ /var/www/html/ && sudo chown -R www-data:www-data /var/www/html/'
```

## 本地预览

```bash
cd /Users/wayne/Documents/Trade/aws/hugo
/usr/local/Homebrew/Cellar/hugo/0.145.0/bin/hugo server -D
# 浏览器开 http://localhost:1313
```

## 加新文章

```bash
hugo new content/posts/your-slug.md
# 编辑文件,把 draft: true 改成 false 或删掉
hugo --minify   # rebuild
# rsync 部署同上
```

## 下次复用(新 VPN VPS)

整个 `hugo/` 文件夹是自包含的(theme 是普通目录不是 submodule),拷贝到任何机器,改 `hugo.toml` 里的 `baseURL`,重新 build + 部署即可。

## 注意

- PaperMod 主题升级:`cd themes/PaperMod && git pull`
- baseURL 必须和实际域名一致,否则 sitemap / RSS 链接会错
- 文章日期(`date:` frontmatter)决定列表顺序
- `draft: true` 的文章不会构建,清理用
