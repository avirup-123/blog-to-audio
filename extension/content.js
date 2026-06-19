(() => {
  const SELECTORS_TO_REMOVE = [
    "nav", "header", "footer", "aside", "form", "script", "style", "noscript",
    ".author-bio", ".author-info", ".byline",
    ".related-posts", ".related-articles",
    ".cta", ".call-to-action",
    ".social-share", ".share-buttons",
    ".comments", "#comments", ".comment-section",
    ".cookie-banner", ".cookie-notice",
    ".breadcrumb", ".breadcrumbs",
    ".sidebar",
    "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    "[role='complementary']"
  ];

  const clone = document.body.cloneNode(true);

  for (const sel of SELECTORS_TO_REMOVE) {
    for (const el of clone.querySelectorAll(sel)) {
      el.remove();
    }
  }

  const article =
    clone.querySelector("article") ||
    clone.querySelector("[role='main']") ||
    clone.querySelector("main") ||
    clone.querySelector(".article-body, .post-body, .entry-content, .post-content, .article-content, .content-body") ||
    clone;

  const text = article.innerText || article.textContent || "";
  return text;
})();
