/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import DOMPurify from "dompurify";

const SANITIZE_CONFIG = {
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
  ALLOWED_ATTR: [
    "style",
    "dir",
    "lang",
    "color",
    "href",
    "title",
    "target",
    "rel",
  ],
  ALLOW_STYLE: true,
  ALLOW_DATA_ATTR: false,
};

/** Sanitize the HTML of an editor (``ckeditor-sanitizer.js`` before). */
export function sanitizeHtml(html) {
  if (!html || typeof html !== "string") {
    return html;
  }
  return DOMPurify.sanitize(html, SANITIZE_CONFIG);
}
