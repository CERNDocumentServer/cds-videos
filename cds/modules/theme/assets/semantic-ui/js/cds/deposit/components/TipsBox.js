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

/** "Tips and suggestions" with the items in ``children``. */
export function TipsBox({ className = "text-muted", children }) {
  return (
    <div className={className}>
      <h5 className="text-muted">
        <strong>Tips and suggestions</strong>
      </h5>
      <ul>{children}</ul>
    </div>
  );
}

TipsBox.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node.isRequired,
};
