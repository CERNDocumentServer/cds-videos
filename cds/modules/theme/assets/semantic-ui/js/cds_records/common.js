/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/*
 * Parts shared by the video and the project pages
 * (static/templates/cds_records/{doi,report_number,keywords}.html).
 */

import React from "react";
import PropTypes from "prop-types";

import { copyToClipboard } from "@js/cds/components/CopyButton";
import { Tooltip } from "@js/cds/components/Popups";
import {
  encodeURIComponentFilter,
  escapeDoubleQuotes,
  get,
} from "@js/cds/utils";

/** doi.html */
export function DoiBadge({ record }) {
  const doi = get(record, "metadata.doi");
  if (!doi) {
    return null;
  }
  return (
    <a
      className="get-badge"
      href={`http://dx.doi.org/${doi}`}
      target="_blank"
      rel="noreferrer"
    >
      <img src={`/badge/doi/${doi}.svg`} alt={doi} />
    </a>
  );
}

DoiBadge.propTypes = { record: PropTypes.object.isRequired };

/** report_number.html: copies the report number on click. */
export function ReportNumberBadge({ record }) {
  const reportNumber = get(record, "metadata.report_number[0]");
  if (!reportNumber) {
    return null;
  }
  return (
    <Tooltip html="<b>Click</b> to copy the Report Number.">
      <a
        className="get-badge"
        href="#copy"
        onClick={(e) => {
          e.preventDefault();
          copyToClipboard(reportNumber);
        }}
      >
        <img
          src={`/badge/rn/${reportNumber}.svg`}
          alt={get(record, "metadata.title.title")}
        />
      </a>
    </Tooltip>
  );
}

ReportNumberBadge.propTypes = { record: PropTypes.object.isRequired };

/** keywords.html */
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
                href={`/search?q=keywords.name:"${encodeURIComponentFilter(
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

/** Text of the record (``ng-bind-html`` with trusted HTML). */
export function Html({ html, as: Component, ...props }) {
  return <Component {...props} dangerouslySetInnerHTML={{ __html: html }} />;
}

Html.propTypes = {
  html: PropTypes.string,
  as: PropTypes.elementType,
};

Html.defaultProps = { html: "", as: "span" };
