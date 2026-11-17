/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/**
 * Markup of a field: label (``*`` when required), widget, then the
 * description or the validation message.
 */

import React from "react";
import PropTypes from "prop-types";
import clsx from "clsx";

export function FormGroup({
  label = null,
  required = false,
  error = null,
  description = null,
  className = null,
  faIcon = null,
  notitle = false,
  nbsp = true,
  noHelp = false,
  children = null,
}) {
  return (
    <div
      className={clsx("field cds-form-group", error && "has-error", className)}
    >
      {!notitle && label && (
        <label className={clsx("control-label", required && "field-required")}>
          {faIcon && <i className={`fa fa-fw ${faIcon}`} />}
          {nbsp && " "}
          {label}
        </label>
      )}
      {children}
      {!noHelp && <div className="help-block">{error || description}</div>}
    </div>
  );
}

FormGroup.propTypes = {
  label: PropTypes.node,
  required: PropTypes.bool,
  error: PropTypes.string,
  description: PropTypes.node,
  className: PropTypes.string,
  faIcon: PropTypes.string,
  notitle: PropTypes.bool,
  nbsp: PropTypes.bool,
  noHelp: PropTypes.bool,
  children: PropTypes.node,
};
