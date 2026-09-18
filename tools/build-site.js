#!/usr/bin/env node
/**
 * Builds the shareable GitHub Pages site from the artifact source files.
 *
 * The files in demo/ are authored as Artifact fragments: no <!doctype>, <html>,
 * <head> or <body>, because claude.ai supplies that wrapper at publish time.
 * This script supplies an equivalent wrapper so the same pages stand alone on
 * any static host, and adds the sharing metadata a link preview needs.
 *
 *   node tools/build-site.js
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "docs");
const BASE = "https://nativeeridian.github.io/claude-experiments";

const PAGES = [
  {
    src: "demo/question-to-artifact.html",
    out: "exec-demo.html",
    description:
      "How an organization modernizes analytics with an LLM: Snowflake owns the metric definitions and the SQL, the model picks the template and writes the artifact. Three worked requests, the MCP and SQL plumbing, and what you actually build."
  },
  {
    src: "demo/insight-stack-demo.html",
    out: "full-demo.html",
    description:
      "The Five-Layer Insight Stack in operation: five worked examples on a fictional distributor, including a refusal, each with its tool trace and a non-removable provenance block."
  }
];

/* The reset claude.ai injects around a published artifact, reproduced so the
   standalone page renders identically. */
const RESET = `:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
body{margin:0;font:14px system-ui,-apple-system,"Segoe UI",sans-serif}
img{max-width:100%}
[hidden]{display:none!important}`;

function esc(s) {
  return String(s).replace(/[&<>"]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
}

function build(page) {
  const raw = fs.readFileSync(path.join(ROOT, page.src), "utf8");

  /* Fragments are authored as: <title>, font <link>s, <style>…</style>, then content.
     Split at the end of that first style block: everything before it belongs in <head>. */
  const cut = raw.indexOf("</style>");
  if (cut === -1) throw new Error(`No <style> block found in ${page.src}`);
  const head = raw.slice(0, cut + "</style>".length);
  const body = raw.slice(cut + "</style>".length);

  const titleMatch = head.match(/<title>([^<]*)<\/title>/i);
  if (!titleMatch) throw new Error(`No <title> found in ${page.src}`);
  const title = titleMatch[1].trim();
  const url = `${BASE}/${page.out}`;

  const doc = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="${esc(page.description)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="LLM-Native Analytics Framework">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(page.description)}">
<meta property="og:url" content="${url}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="${esc(title)}">
<meta name="twitter:description" content="${esc(page.description)}">
<link rel="canonical" href="${url}">
<style>${RESET}</style>
${head}
</head>
<body>
${body.trim()}
</body>
</html>
`;

  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, page.out), doc);
  console.log(`  ${page.src} -> docs/${page.out}  (${(doc.length / 1024).toFixed(0)} KB)`);
}

console.log("Building shareable site into docs/");
PAGES.forEach(build);
fs.writeFileSync(path.join(OUT, ".nojekyll"), "");
console.log("  docs/.nojekyll");
console.log("Done. Serve docs/ from GitHub Pages.");
