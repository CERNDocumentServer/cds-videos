/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/*
 * HugeRTE, the editor of Invenio's forms (react-invenio-forms), with the
 * plugins of the CDS toolbars. Loaded with the first editor of the page.
 * Its skins are copied to ``static/dist/js/skins`` by Invenio-Administration.
 */

import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Editor } from "@hugerte/hugerte-react";
import "hugerte/hugerte";
import "hugerte/models/dom/model";
import "hugerte/themes/silver";
import "hugerte/icons/default";
import "hugerte/plugins/autoresize";
import "hugerte/plugins/code";
import "hugerte/plugins/link";
import "hugerte/plugins/lists";
import "hugerte/plugins/searchreplace";

import { sanitizeHtml } from "./sanitize";

export const MIN_HEIGHT = 250;

const CONFIG = {
  branding: false,
  menubar: false,
  statusbar: false,
  contextmenu: false,
  plugins: ["autoresize", "code", "link", "lists", "searchreplace"],
  toolbar_mode: "wrap",
  min_height: MIN_HEIGHT,
  autoresize_bottom_margin: 20,
  // Enter adds a line break, as the descriptions were written with CKEditor
  newline_behavior: "linebreak",
  // Characters as they are, apart from the non-breaking space
  entity_encoding: "named",
  entities: "160,nbsp",
  convert_urls: false,
  link_target_list: [
    { title: "Current window", value: "" },
    { title: "New window", value: "_blank" },
  ],
  content_style: "body { font-size: 14px; }",
};

/**
 * The descriptions are lines separated by ``<br>``. HugeRTE always puts the
 * text in a paragraph: drop it when it is the only one.
 */
export function unwrapParagraph(html) {
  const match = /^<p>([\s\S]*)<\/p>$/.exec(html);
  return match && !/<\/?p\b/i.test(match[1]) ? match[1] : html;
}

function contentOf(instance) {
  return sanitizeHtml(unwrapParagraph(instance.getContent()));
}

export default function RichTextEditor({
  value = "",
  disabled = false,
  toolbar,
  onChange,
  onReady,
}) {
  const [initialValue] = useState(value || "");
  const editor = useRef(null);
  // The value of the editor, as last sent or received
  const current = useRef(null);
  const setting = useRef(false);

  // Values changed from outside (inherited or extracted metadata, saves)
  useEffect(() => {
    const instance = editor.current;
    if (instance && (value || "") !== current.current) {
      setting.current = true;
      instance.setContent(value || "");
      setting.current = false;
      current.current = contentOf(instance);
    }
  }, [value]);

  return (
    <Editor
      initialValue={initialValue}
      disabled={disabled}
      init={{ ...CONFIG, toolbar }}
      onInit={(event, instance) => {
        editor.current = instance;
        current.current = contentOf(instance);
        onReady();
      }}
      onEditorChange={(content, instance) => {
        if (setting.current || !editor.current) return;
        const html = contentOf(instance);
        if (html !== current.current) {
          current.current = html;
          onChange(html);
        }
      }}
    />
  );
}

RichTextEditor.propTypes = {
  value: PropTypes.string,
  disabled: PropTypes.bool,
  toolbar: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  onReady: PropTypes.func.isRequired,
};
