/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* static/templates/cds_records/video/related_event_section.html */

import React from "react";
import PropTypes from "prop-types";

import { SearchWidget } from "@js/cds/components/SearchWidget";
import { useSearch } from "@js/cds/search/hooks";
import { angularFilterBy, get } from "@js/cds/utils";

function Header({ identifier }) {
  const [state] = useSearch();
  const hits = state.results.hits;
  if (!(hits && hits.total > 0)) {
    return null;
  }
  return (
    <div>
      <hr />
      <div className="cds-title-section custom-flex-row">
        <h4 className="cds-title-section-decoration bw-2 mb-10">
          More videos from this event
        </h4>
        <a
          href={`/search?q=related_identifiers.identifier:${identifier}`}
          className="explore-link t-b"
        >
          Explore all <i className="fa fa-chevron-right" />
        </a>
      </div>
    </div>
  );
}

Header.propTypes = { identifier: PropTypes.string };
Header.defaultProps = { identifier: undefined };

export function RelatedEventSection({ record, relatedQueryUrl }) {
  const indicoIdentifier =
    angularFilterBy(get(record, "metadata.related_identifiers"), {
      scheme: "indico",
    })[0] || {};
  const endpoint = (relatedQueryUrl || "").replace(
    "%s",
    "related_identifiers.identifier:" +
      indicoIdentifier.identifier +
      " AND -recid:" +
      record.metadata.recid
  );
  return (
    <div>
      <div className="cds-dynamic-results bg-w custom-video-style">
        <SearchWidget endpoint={endpoint} template="medium" withLoading={false}>
          <Header identifier={indicoIdentifier.identifier} />
        </SearchWidget>
      </div>
    </div>
  );
}

RelatedEventSection.propTypes = {
  record: PropTypes.object.isRequired,
  relatedQueryUrl: PropTypes.string,
};

RelatedEventSection.defaultProps = { relatedQueryUrl: "" };
