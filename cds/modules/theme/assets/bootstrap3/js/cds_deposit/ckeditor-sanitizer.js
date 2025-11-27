/**
 * CKEditor HTML Sanitizer
 * Sanitizes HTML content using DOMPurify to prevent XSS attacks
 */
import DOMPurify from "dompurify";

// Sanitization config - matches backend allowed tags
var sanitizeConfig = {
  ALLOWED_TAGS: [
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "br",
    "code",
    "col",
    "colgroup",
    "div",
    "table",
    "tbody",
    "tfoot",
    "thead",
    "td",
    "th",
    "tr",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strike",
    "strong",
    "sub",
    "sup",
    "u",
    "ul",
  ],
  ALLOWED_ATTR: ["style", "dir", "lang", "color"],
  ALLOW_STYLE: true,
  ALLOW_DATA_ATTR: false,
};

function sanitizeHtml(html) {
  if (!html || typeof html !== "string") {
    return html;
  }
  return DOMPurify.sanitize(html, sanitizeConfig);
}

// Initialize sanitization when CKEditor instances are ready
if (typeof window !== "undefined" && window.CKEDITOR) {
  window.CKEDITOR.on("instanceReady", function (ev) {
    var editor = ev.editor;

    // Store original getData method
    var originalGetData = editor.getData;

    // Sanitize when content is retrieved (before saving)
    editor.getData = function (noEvents) {
      var data = originalGetData.call(this, noEvents);
      if (data) {
        return sanitizeHtml(data);
      }
      return data;
    };
  });
}

