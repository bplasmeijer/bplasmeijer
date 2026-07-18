# AI Agent Instructions for bartplasmeijer.nl

Single-page static HTML site (no build tooling, no Hugo, no framework). Hosted on GitHub Pages.

## Structure

```
site/
  index.html        # entire page content, sections in DOM order
  assets/
    style.css        # dark theme, scroll-reveal transforms
    script.js        # IntersectionObserver reveal logic
Profile.pdf          # source content for the page (LinkedIn export)
.github/workflows/deploy.yml   # deploys ./site to GitHub Pages on push to main
```

## Editing content

All copy lives directly in [site/index.html](site/index.html) — there is no templating or content pipeline. To update experience/skills/summary, edit the relevant `<section>` by hand, sourcing facts from [Profile.pdf](Profile.pdf) if it changes.

## Local preview

No build step needed:

```bash
cd site && python3 -m http.server 8000
```

Open `http://localhost:8000`.

## Deployment

[.github/workflows/deploy.yml](.github/workflows/deploy.yml) uploads `./site` as a Pages artifact and deploys on every push to `main`. No submodules, no Hugo, no Node build.

## Notes

- Reduced-motion users get animations disabled via `prefers-reduced-motion` in `style.css`.
- Previous Hugo blog (posts, LinkedIn import workflow, theme submodules) was removed in favor of this single-page profile site.
