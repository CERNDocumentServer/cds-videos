/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { prevent } from "@js/cds/shared/dom";

import { useReadonly } from "./formContext";

/** Collapsible group of fields, disabled when the form is read only. */
export function Fieldset({ title, description = null, children = null }) {
  const [collapsed, setCollapsed] = useState(false);
  const disabled = useReadonly();
  return (
    <fieldset className="schema-form-fieldset" disabled={disabled}>
      <div className="cds-panel deposit-panel">
        <div className="cds-panel-heading">
          <a
            className="panel-toggle"
            href="#toggle"
            onClick={prevent(() => setCollapsed(!collapsed))}
          >
            {title}
            <span className="pull-right">
              <i
                className={`fa ${
                  collapsed ? "fa-chevron-right" : "fa-chevron-down"
                }`}
              />
            </span>
          </a>
        </div>
        <div
          className="cds-panel-body"
          style={{ display: collapsed ? "none" : undefined }}
        >
          {description && <p>{description}</p>}
          {children}
        </div>
      </div>
    </fieldset>
  );
}

Fieldset.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.node,
  children: PropTypes.node,
};
