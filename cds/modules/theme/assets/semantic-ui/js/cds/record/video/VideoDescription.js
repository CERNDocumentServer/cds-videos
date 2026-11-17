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

import { TrustedHtml } from "../components/TrustedHtml";
import { sanitize } from "./sanitize";
import {
  Contributors,
  LanguageAndProject,
  Licences,
  RelatedIdentifiers,
  RelatedLinks,
} from "./DescriptionDetails";

/**
 * Description of a video, short until ``expanded``, then its details.
 * Clicking a timestamp of the description calls ``onJump`` with its seconds.
 */
export function VideoDescription({
  record,
  shortDescription,
  fullDescription,
  groupedRelatedIdentifiers,
  expanded,
  onToggle,
  onJump,
}) {
  const onDescriptionClick = (event) => {
    const link =
      event.target.closest && event.target.closest("a.timestamp-link");
    if (link) {
      event.preventDefault();
      try {
        onJump(parseInt(link.dataset.seconds, 10));
      } catch (e) {
        console.error("Could not seek to timestamp:", e);
      }
    }
  };

  return (
    <div
      className="cds-detail-description cds-detail-video-description t-b px-20"
      onClick={onDescriptionClick}
      role="presentation"
    >
      <TrustedHtml
        as="p"
        className="mb-30"
        html={
          sanitize(expanded ? fullDescription : shortDescription) ||
          "No description"
        }
      />
      {/* Hidden content */}
      <div
        className="mt-20"
        style={{
          display: expanded ? undefined : "none",
        }}
      >
        <Contributors record={record} />
        <div className="mb-10">
          <Licences record={record} />
          <LanguageAndProject record={record} />
        </div>
      </div>
      <RelatedLinks record={record} />
      <RelatedIdentifiers
        groupedRelatedIdentifiers={groupedRelatedIdentifiers}
      />
      <div
        className="text-center"
        style={{
          display: expanded ? "none" : undefined,
        }}
      >
        <button
          type="button"
          className="cds-btn-link cds-btn-sm"
          onClick={() => onToggle()}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      </div>
    </div>
  );
}

VideoDescription.propTypes = {
  record: PropTypes.object.isRequired,
  shortDescription: PropTypes.string,
  fullDescription: PropTypes.string,
  groupedRelatedIdentifiers: PropTypes.object.isRequired,
  expanded: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  onJump: PropTypes.func.isRequired,
};
