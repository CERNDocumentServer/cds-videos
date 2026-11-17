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

/** Bootstrap like progress bar. */
export function ProgressBar({
  striped = false,
  active = false,
  success = false,
  width = 100,
  children = null,
}) {
  return (
    <div className="cds-progress">
      <div
        className={[
          "cds-progress-bar",
          striped && "cds-progress-bar-striped",
          active && "active",
          success && "cds-progress-bar-success",
        ]
          .filter(Boolean)
          .join(" ")}
        role="progressbar"
        style={{ width: `${width}%` }}
      >
        {children}
      </div>
    </div>
  );
}

ProgressBar.propTypes = {
  striped: PropTypes.bool,
  active: PropTypes.bool,
  success: PropTypes.bool,
  width: PropTypes.number,
  children: PropTypes.node,
};
