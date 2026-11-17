/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Description field, with the editor loaded on first use. */

import React, { Suspense, lazy, useState } from "react";
import PropTypes from "prop-types";
import { Placeholder } from "semantic-ui-react";

import { sanitizeHtml } from "./sanitize";
import { useDepositField, useReadonly } from "./formContext";
import { FormGroup } from "./FormGroup";

/**
 * The content of an editor while HugeRTE loads: the text is readable at
 * once, in a box of the size of the editor.
 */
function RichTextLoading({ html = "" }) {
  return (
    <div className="cds-rich-text-loading" aria-busy="true">
      <div className="cds-rich-text-loading-toolbar">
        <Placeholder className="cds-placeholder">
          <Placeholder.Line length="full" />
        </Placeholder>
      </div>
      <div
        className="cds-rich-text-loading-content"
        dangerouslySetInnerHTML={{ __html: sanitizeHtml(html || "") }}
      />
    </div>
  );
}

RichTextLoading.propTypes = { html: PropTypes.string };

// HugeRTE (about 1 MB) is loaded with the first editor, after the form is
// shown
const RichTextEditor = lazy(() => import("./RichTextEditor"));

export function RichTextField({
  name,
  label = null,
  description = null,
  required = false,
  toolbar,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  const [ready, setReady] = useState(false);
  const loading = <RichTextLoading html={value} />;
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      nbsp={false}
      noHelp
    >
      <Suspense fallback={loading}>
        {!ready && loading}
        <div className={ready ? undefined : "cds-rich-text-starting"}>
          <RichTextEditor
            value={value}
            disabled={disabled}
            toolbar={toolbar}
            onChange={setValue}
            onReady={() => setReady(true)}
          />
        </div>
      </Suspense>
      <span className="help-block">{error || description}</span>
    </FormGroup>
  );
}

RichTextField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
  toolbar: PropTypes.string.isRequired,
};
