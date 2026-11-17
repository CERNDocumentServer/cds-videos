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

import { Tooltip } from "@js/cds/shared/components/Popups";
import { get, groupBy } from "@js/cds/shared/utils/collections";
import { isPublic } from "@js/cds/shared/utils/records";
import { replace } from "@js/cds/shared/utils/text";
import { formatDate } from "@js/cds/shared/utils/dates";

import { DoiBadge, ReportNumberBadge } from "../components/Badges";
import { OtherLicense } from "./Licenses";
import { Translations } from "./Translations";

/**
 * Top of the video metadata: edit link, access, DOI and report number,
 * title, then copyright, licence, date, duration and views.
 */
export function VideoHeader({ record, recordViews = undefined }) {
  const metadata = record.metadata;
  const licenses = groupBy(metadata.license, "material", "other");
  const reportNumber = get(metadata, "report_number[0]");
  return (
    <>
      {/* DOI and report number */}
      <div className="px-20">
        <div className="cds-row">
          <div className="cds-col-md-2">
            <ul
              className="cds-list-inline"
              style={{
                display: get(record, "links.project_edit") ? undefined : "none",
              }}
            >
              <li>
                <a
                  href={get(record, "links.project_edit")}
                  title="Edit the record"
                >
                  <i className="fa fa-edit" /> edit
                </a>
              </li>
            </ul>
          </div>
          <div className="cds-col-md-10">
            <ul className="cds-list-inline text-right">
              {isPublic(metadata) ? (
                <li>
                  <Tooltip html="This record is <b>public</b>.">
                    <span className="ui label cds-label cds-label-success">
                      Public
                    </span>
                  </Tooltip>
                </li>
              ) : (
                <li>
                  <Tooltip html="This record is <b>restricted</b>.">
                    <span className="ui label cds-label cds-label-warning">
                      Restricted
                    </span>
                  </Tooltip>
                </li>
              )}{" "}
              {metadata.doi && (
                <li>
                  <DoiBadge record={record} />
                </li>
              )}{" "}
              {reportNumber && (
                <li className="pr-0">
                  <ReportNumberBadge record={record} />
                </li>
              )}{" "}
            </ul>
          </div>
        </div>
      </div>
      {/* Title */}
      <div className="cds-detail-title cds-detail-video-title mt-20 px-20">
        <hgroup>
          <h1 className="mb-0 mt-0 f4 fw-n t-b">
            {get(metadata, "title.title")} <Translations record={record} />
          </h1>
        </hgroup>
      </div>
      {/* Date & Views */}
      <div className="cds-detail-date cds-detail-video-date mb-30 px-20 my-20 f8">
        <ul className="cds-list-inline mb-0">
          <Tooltip html="Copyright">
            <li>
              <i className="fa fa-copyright text-muted" />{" "}
              {get(metadata, "copyright.year")}{" "}
              {get(metadata, "copyright.holder")}
            </li>
          </Tooltip>{" "}
          {Object.entries(licenses)
            .filter(([material]) => material === "other")
            .map(([material, items]) => (
              <OtherLicense key={material} licenses={items} />
            ))}{" "}
          <Tooltip html="Date">
            <li>
              <i className="fa fa-calendar text-muted" />{" "}
              {formatDate(metadata.date, "dd MMMM yyyy")}
            </li>
          </Tooltip>{" "}
          <Tooltip html="Video duration">
            <li>
              <i className="fa fa-clock-o text-muted" />{" "}
              {replace(metadata.duration, ".000", "")}
            </li>
          </Tooltip>{" "}
          <li className="pull-right">{recordViews || 0} Views</li>
        </ul>
      </div>
    </>
  );
}

VideoHeader.propTypes = {
  record: PropTypes.object.isRequired,
  recordViews: PropTypes.number,
};
