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
import DOMPurify from "dompurify";

/** Trusted HTML of the record, sanitized. */
export function SanitizedHtml({
  html = "",
  as: Component = "p",
  className = null,
}) {
  return (
    <Component
      className={className || undefined}
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html || "") }}
    />
  );
}

SanitizedHtml.propTypes = {
  html: PropTypes.string,
  as: PropTypes.elementType,
  className: PropTypes.string,
};
