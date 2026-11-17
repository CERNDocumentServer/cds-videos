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

/** Bootstrap like tabs. */
export function Tabs({ active, onChange, tabs }) {
  return (
    <div className="ui tabular menu cds-nav-tabs" role="tablist">
      {tabs
        .filter((tab) => !tab.hidden)
        .map((tab) => (
          <a
            key={tab.key}
            href={`#${tab.key}`}
            role="tab"
            className={`item${active === tab.key ? " active" : ""}`}
            onClick={(e) => {
              e.preventDefault();
              onChange(tab.key);
            }}
          >
            {tab.title}
          </a>
        ))}
    </div>
  );
}

Tabs.propTypes = {
  active: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  tabs: PropTypes.array.isRequired,
};
