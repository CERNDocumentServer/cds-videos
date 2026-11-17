/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** DOI and report number badges of a record. */

import React from "react";
import PropTypes from "prop-types";

import { copyToClipboard } from "@js/cds/shared/components/CopyButton";
import { Tooltip } from "@js/cds/shared/components/Popups";
import { get } from "@js/cds/shared/utils/collections";

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

/** Report number badge, copies the report number on click. */
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
