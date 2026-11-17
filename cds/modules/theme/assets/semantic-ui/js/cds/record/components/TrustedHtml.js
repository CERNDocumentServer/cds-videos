/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** HTML of a record rendered as is, without sanitizing it. */

import React from "react";
import PropTypes from "prop-types";

export function TrustedHtml({ html = "", as: Component = "span", ...props }) {
  return <Component {...props} dangerouslySetInnerHTML={{ __html: html }} />;
}

TrustedHtml.propTypes = {
  html: PropTypes.string,
  as: PropTypes.elementType,
};
