/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React from "react";
import PropTypes from "prop-types";
import { Button } from "semantic-ui-react";

/** Copy a text to the clipboard (with a fallback for insecure contexts). */
export function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  const tmp = document.createElement("textarea");
  tmp.value = text;
  tmp.setAttribute("readonly", "");
  tmp.style.position = "absolute";
  tmp.style.left = "-9999px";
  document.body.appendChild(tmp);
  tmp.select();
  try {
    document.execCommand("copy");
  } catch (e) {
    // Nothing to do
  }
  document.body.removeChild(tmp);
  return Promise.resolve();
}

/** Button copying a text, or the value of an input (replaces ngclipboard). */
export function CopyButton({
  text = null,
  targetId = null,
  children = null,
  ...props
}) {
  const onClick = () => {
    let value = text;
    if (targetId) {
      const target = document.getElementById(targetId);
      if (target) {
        value = target.value;
        target.select && target.select();
      }
    }
    copyToClipboard(value || "");
  };
  return (
    <Button type="button" basic icon onClick={onClick} {...props}>
      {children || <i className="fa fa-copy" />}
    </Button>
  );
}

CopyButton.propTypes = {
  text: PropTypes.string,
  targetId: PropTypes.string,
  children: PropTypes.node,
};
