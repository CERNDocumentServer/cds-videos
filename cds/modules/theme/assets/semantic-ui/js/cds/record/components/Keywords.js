/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Keywords of a record, each linking to a search. */

import React from "react";
import PropTypes from "prop-types";

import { get } from "@js/cds/shared/utils/collections";
import { escapeDoubleQuotes } from "@js/cds/shared/utils/text";

export function Keywords({ record }) {
  const keywords = get(record, "metadata.keywords") || [];
  if (!(keywords.length > 0)) {
    return null;
  }
  return (
    <div className="cds-detail cds-detail-video cds-div-shadow bg-w pt-10 px-20 pb-10 mb-30 mt-20 t-b">
      <div className="cds-detail-title cds-detail-video-title">
        <h3 className="cds-title-section-decoration bt bw-1 pt-10 mb-20">
          <i className="fa fa-tags" /> Keywords
        </h3>
      </div>
      <div className="cds-tags cds-keywords">
        <ul>
          {keywords.map((keyword, index) => (
            <li key={index}>
              <a
                href={`/search?q=keywords.name:"${encodeURIComponent(
                  escapeDoubleQuotes(keyword.name)
                )}"`}
              >
                {keyword.name}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

Keywords.propTypes = { record: PropTypes.object.isRequired };
