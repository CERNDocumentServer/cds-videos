/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* static/templates/cds_records/video/technical_metadata.html */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { findMaster } from "@js/cds/utils";

export function TechnicalMetadata({ record }) {
  const [technicalExpand, setTechnicalExpand] = useState(false);
  const tags = (findMaster(record) || {}).tags;
  return (
    <div>
      <div className="cds-detail-title cds-detail-video-title">
        <h3 className="cds-title-section-decoration bt bw-1 pt-10 mb-20">
          <i className="fa fa-cogs" /> Technical Metadata
        </h3>
      </div>
      <div
        className="text-center"
        style={{ display: tags ? "none" : undefined }}
      >
        <p className="text-muted">Not available</p>
      </div>
      <div
        className="cds-detail-download-box cds-detail-video-download-box cds-transition"
        style={{ display: tags ? undefined : "none" }}
      >
        {Object.keys(tags || {}).map((key, index) => (
          <ul key={key}>
            <li
              style={{
                display:
                  (index > 2 && !technicalExpand) || key[0] === "_"
                    ? "none"
                    : undefined,
              }}
            >
              <b>{key}:</b> {String(tags[key])}
            </li>
          </ul>
        ))}
      </div>
      <div className="text-right">
        <a
          className="f8 display-block"
          href="#expand"
          onClick={(e) => {
            e.preventDefault();
            setTechnicalExpand(!technicalExpand);
          }}
        >
          <p className="mb-0">
            <span>
              <i
                className={`fa f5 ${
                  technicalExpand ? "fa-angle-up" : "fa-angle-down"
                }`}
              />
            </span>
          </p>
        </a>
      </div>
    </div>
  );
}

TechnicalMetadata.propTypes = { record: PropTypes.object.isRequired };
