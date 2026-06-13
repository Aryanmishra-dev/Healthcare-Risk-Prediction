import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const templatesDir = path.join(root, "src", "pages", "templates");
const distDir = path.join(root, "dist");
const initialTab = "home";

function normalizeApiUrl(value) {
  return (value || "").trim().replace(/\/+$/, "");
}

function escapeForDoubleQuotedString(value) {
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function readTemplate(templatePath) {
  return fs.readFileSync(path.join(templatesDir, templatePath), "utf8");
}

function extractBlock(source, name) {
  const pattern = new RegExp(String.raw`\{% block ${name} %\}([\s\S]*?)\{% endblock %\}`);
  const match = source.match(pattern);
  return match ? match[1].trim() : "";
}

function renderInitialTabConditionals(html) {
  let output = html;
  const withFallback = /\{% if initial_tab == '([^']+)' or not initial_tab %\}([\s\S]*?)\{% else %\}([\s\S]*?)\{% endif %\}/g;
  const simple = /\{% if initial_tab == '([^']+)' %\}([\s\S]*?)\{% else %\}([\s\S]*?)\{% endif %\}/g;
  output = output.replace(withFallback, (_match, tab, yes, no) => (initialTab === tab ? yes : no));
  output = output.replace(simple, (_match, tab, yes, no) => (initialTab === tab ? yes : no));
  output = output.replace(/\{% if initial_tab == '([^']+)' or not initial_tab %\}([\s\S]*?)\{% endif %\}/g, (_match, tab, yes) =>
    initialTab === tab ? yes : ""
  );
  output = output.replace(/\{% if initial_tab == '([^']+)' %\}([\s\S]*?)\{% endif %\}/g, (_match, tab, yes) =>
    initialTab === tab ? yes : ""
  );
  return output;
}

function parseTupleList(html, name) {
  const match = html.match(new RegExp(String.raw`\{% set ${name} = \[([\s\S]*?)\] %\}`));
  if (!match) return [];
  return [...match[1].matchAll(/\("([^"]+)",\s*"([^"]+)"\)/g)].map((entry) => [entry[1], entry[2]]);
}

function parseStringList(html, name) {
  const match = html.match(new RegExp(String.raw`\{% set ${name} = \[([\s\S]*?)\] %\}`));
  if (!match) return [];
  return [...match[1].matchAll(/"([^"]+)"/g)].map((entry) => entry[1]);
}

function renderLoopBlock(block, values) {
  let output = block.replace(/\{% if not loop\.last %\}([\s\S]*?)\{% endif %\}/g, values.loop.last ? "" : "$1");
  output = output.replace(/\{\{\s*loop\.index\s*\}\}/g, String(values.loop.index));
  output = output.replace(/\{\{\s*icon\s*\}\}/g, values.icon || "");
  output = output.replace(/\{\{\s*label\s*\}\}/g, values.label || "");
  output = output.replace(/\{\{\s*step\s*\}\}/g, values.step || "");
  return output;
}

function renderAboutLoops(html) {
  const pipelineSteps = parseTupleList(html, "pipeline_steps");
  const workflowSteps = parseStringList(html, "workflow_steps");
  let output = html
    .replace(/\{% set pipeline_steps = \[[\s\S]*?\] %\}/g, "")
    .replace(/\{% set workflow_steps = \[[\s\S]*?\] %\}/g, "");

  output = output.replace(/\{% for icon, label in pipeline_steps %\}([\s\S]*?)\{% endfor %\}/g, (_match, block) =>
    pipelineSteps
      .map(([icon, label], index) =>
        renderLoopBlock(block, {
          icon,
          label,
          loop: { index: index + 1, last: index === pipelineSteps.length - 1 },
        })
      )
      .join("")
  );
  output = output.replace(/\{% for step in workflow_steps %\}([\s\S]*?)\{% endfor %\}/g, (_match, block) =>
    workflowSteps
      .map((step, index) =>
        renderLoopBlock(block, {
          step,
          loop: { index: index + 1, last: index === workflowSteps.length - 1 },
        })
      )
      .join("")
  );
  return output;
}

function renderIncludes(html, context) {
  let output = html.replace(
    /\{% set widget_id = '([^']+)' %\}\s*\{% include "partials\/upload_widget.html" %\}/g,
    (_match, widgetId) => renderTemplate("partials/upload_widget.html", { ...context, widget_id: widgetId })
  );

  let previous;
  do {
    previous = output;
    output = output.replace(/\{% include "([^"]+)" %\}/g, (_match, includePath) => renderTemplate(includePath, context));
  } while (output !== previous);

  return output;
}

function renderVariables(html, context) {
  return html
    .replace(/\{\{\s*widget_id\s*\}\}/g, context.widget_id || "")
    .replace(/\{\{\s*initial_tab\|default\("home"\)\s*\}\}/g, initialTab)
    .replace(/\{\{\s*BACKEND_URL\s*\}\}/g, process.env.BACKEND_URL || process.env.VITE_API_URL || "");
}

function renderTemplate(templatePath, context = {}) {
  let html = readTemplate(templatePath);
  html = renderIncludes(html, context);
  html = renderAboutLoops(html);
  html = renderInitialTabConditionals(html);
  html = renderVariables(html, context);
  return html;
}

function assertNoUnrenderedJinja(html) {
  const unrendered = html.match(/\{%|\{\{/g);
  if (unrendered) {
    throw new Error("Static build left unrendered Jinja tags in dist/index.html");
  }
}

function copyDir(source, target) {
  fs.cpSync(source, target, { recursive: true });
}

const apiUrl = escapeForDoubleQuotedString(normalizeApiUrl(process.env.VITE_API_URL));
if (!apiUrl) {
  throw new Error("VITE_API_URL is required for the frontend static build");
}

const indexTemplate = readTemplate("index.html");
const baseTemplate = readTemplate("base.html");

const body = renderInitialTabConditionals(renderTemplate("index.html")).replace(/\{% extends "base.html" %\}/, "");
const renderedBody = extractBlock(body, "body");
const renderedScripts = extractBlock(indexTemplate, "scripts");

let html = baseTemplate
  .replace(/\{% block title %\}([\s\S]*?)\{% endblock %\}/, "$1")
  .replace(/\{% block extra_head %\}([\s\S]*?)\{% endblock %\}/, "")
  .replace(/\{% block body %\}([\s\S]*?)\{% endblock %\}/, renderedBody)
  .replace(/\{% block scripts %\}([\s\S]*?)\{% endblock %\}/, renderInitialTabConditionals(renderVariables(renderedScripts, {})))
  .replace(/__HEALTHPREDICT_API_URL__/g, apiUrl);

html = renderVariables(renderInitialTabConditionals(html), {});
assertNoUnrenderedJinja(html);

fs.rmSync(distDir, { recursive: true, force: true });
fs.mkdirSync(distDir, { recursive: true });
copyDir(path.join(root, "src", "assets"), path.join(distDir, "static"));
copyDir(path.join(root, "src", "styles"), path.join(distDir, "styles"));
fs.writeFileSync(path.join(distDir, "index.html"), html, "utf8");

console.log(`Built frontend to ${path.relative(root, distDir)}`);
