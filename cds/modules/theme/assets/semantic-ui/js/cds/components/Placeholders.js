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
 * Semantic UI placeholders shown while a search is loading. They mirror the
 * layout of the result templates so the page does not jump when the results
 * arrive.
 */

import React from "react";
import PropTypes from "prop-types";
import { Placeholder } from "semantic-ui-react";

function range(count) {
  return Array.from({ length: count }, (_, index) => index);
}

/** A text line, e.g. in place of the result count. */
export function LinePlaceholder({ className }) {
  return (
    <Placeholder
      className={["cds-placeholder cds-placeholder-text", className]
        .filter(Boolean)
        .join(" ")}
    >
      <Placeholder.Header>
        <Placeholder.Line length="full" />
      </Placeholder.Header>
    </Placeholder>
  );
}

LinePlaceholder.propTypes = { className: PropTypes.string };
LinePlaceholder.defaultProps = { className: null };

/** A video thumbnail with its title. */
function VideoCardPlaceholder({ dark }) {
  return (
    <Placeholder
      fluid
      inverted={dark}
      className={`cds-placeholder${dark ? " cds-placeholder-dark" : ""}`}
    >
      <Placeholder.Image className="cds-placeholder-thumbnail" />
      <Placeholder.Paragraph>
        <Placeholder.Line length="very long" />
        <Placeholder.Line length="medium" />
      </Placeholder.Paragraph>
    </Placeholder>
  );
}

VideoCardPlaceholder.propTypes = { dark: PropTypes.bool.isRequired };

/** A grid of videos, like the grid templates of ``VideoTemplates``. */
export function VideoGridPlaceholder({ count, columnClass, perRow, dark }) {
  return (
    <div className="cds-row cds-search-results" aria-busy="true">
      {range(count).map((index) => (
        <React.Fragment key={index}>
          <div className={columnClass}>
            <VideoCardPlaceholder dark={dark} />
          </div>
          {perRow > 0 && !((index + 1) % perRow) && (
            <div className="cds-clearfix-md" />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

VideoGridPlaceholder.propTypes = {
  count: PropTypes.number.isRequired,
  columnClass: PropTypes.string.isRequired,
  perRow: PropTypes.number,
  dark: PropTypes.bool,
};

VideoGridPlaceholder.defaultProps = { perRow: 0, dark: false };

/** The featured video player of the home page. */
export function FeaturedVideoPlaceholder() {
  return (
    <div className="bg-b" aria-busy="true">
      <div className="cds-video-iframe">
        <Placeholder
          inverted
          className="cds-placeholder cds-placeholder-black cds-placeholder-player"
        >
          <Placeholder.Image />
        </Placeholder>
      </div>
    </div>
  );
}

/** Placeholders of the ``VIDEO_TEMPLATES``, by template name. */
export const VIDEO_PLACEHOLDERS = {
  featured: FeaturedVideoPlaceholder,
  "featured-medium": () => (
    <VideoGridPlaceholder count={3} columnClass="cds-col-md-4" dark />
  ),
  medium: () => <VideoGridPlaceholder count={3} columnClass="cds-col-md-4" />,
  small: () => (
    <VideoGridPlaceholder
      count={6}
      columnClass="cds-col-md-4 mb-20"
      perRow={3}
    />
  ),
  "small-video-card": () => (
    <VideoGridPlaceholder count={4} columnClass="cds-col-md-3" />
  ),
};

/** The facet boxes of the search pages. */
export function FacetsPlaceholder({ count }) {
  return (
    <div aria-busy="true">
      {range(count).map((index) => (
        <div key={index} className="cds-border ba mb-30 pa-10 b-r-3">
          <Placeholder fluid className="cds-placeholder cds-placeholder-facet">
            <Placeholder.Header>
              <Placeholder.Line length="short" />
            </Placeholder.Header>
            <Placeholder.Paragraph>
              <Placeholder.Line length="long" />
              <Placeholder.Line length="medium" />
              {index % 2 === 0 && <Placeholder.Line length="long" />}
            </Placeholder.Paragraph>
          </Placeholder>
        </div>
      ))}
    </div>
  );
}

FacetsPlaceholder.propTypes = { count: PropTypes.number };
FacetsPlaceholder.defaultProps = { count: 3 };
