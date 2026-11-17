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
 * Templates rendering the results of video searches: home page sections,
 * related videos and the search page.
 */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { ProgressiveImage } from "@js/cds/shared/components/ProgressiveImage";
import { findMaster } from "@js/cds/shared/utils/records";
import { getImagePreview } from "@js/cds/shared/utils/images";
import { ellipsis } from "@js/cds/shared/utils/text";
import { previewIframeSrc } from "@js/cds/shared/utils/urls";

function hitsOf(results) {
  return (results && results.hits && results.hits.hits) || [];
}

function title(record, length) {
  return ellipsis(record.metadata.title.title || "No title", length);
}

/** Player of the featured video. */
export function FeaturedVideo({ results }) {
  return (
    <div className="bg-b">
      {hitsOf(results).map((record, index) => (
        <div className="cds-video-iframe text-center" key={record.id || index}>
          {index === 0 && record.id && (
            <iframe
              title="Featured video"
              scrolling="no"
              width="100%"
              height="100%"
              frameBorder="0"
              src={previewIframeSrc(record.id, (findMaster(record) || {}).key)}
              allowFullScreen
            />
          )}
        </div>
      ))}
    </div>
  );
}

FeaturedVideo.propTypes = { results: PropTypes.object.isRequired };

/** Most recent videos on the home page. */
export function FeaturedMediumGrid({ results }) {
  return (
    <div className="cds-row cds-search-results">
      {hitsOf(results).map((record, index) => (
        <FeaturedMediumItem key={index} record={record} />
      ))}
    </div>
  );
}

FeaturedMediumGrid.propTypes = { results: PropTypes.object.isRequired };

function FeaturedMediumItem({ record }) {
  const [show, setShow] = useState(false);
  return (
    <div className="cds-col-md-4">
      <a
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className={`cds-transition cds-video-title l-w cds-line-height-100${
          show ? "" : " cds-video-title-with-play-button"
        }`}
        target="_self"
        href={`/record/${record.id}`}
      >
        <ProgressiveImage
          className="img-responsive"
          gifSrc={getImagePreview(record, true, [400, 220])}
          imgSrc={getImagePreview(record, false, [400, 220])}
        />
        <p>{title(record, 60)}</p>
      </a>
      <p
        className={`cds-transition t-w ${
          show ? "cds-visibility-visible" : "cds-visibility-hidden"
        }`}
        dangerouslySetInnerHTML={{
          __html: ellipsis(record.metadata.description || "", 60),
        }}
      />
    </div>
  );
}

FeaturedMediumItem.propTypes = { record: PropTypes.object.isRequired };

/** Related videos. */
export function MediumGrid({ results }) {
  return (
    <div className="cds-row cds-search-results">
      {hitsOf(results).map((record, index) => (
        <MediumItem key={index} record={record} />
      ))}
    </div>
  );
}

MediumGrid.propTypes = { results: PropTypes.object.isRequired };

function MediumItem({ record }) {
  const [show, setShow] = useState(false);
  return (
    <div className="cds-col-md-4">
      <a
        className={`cds-transition cds-video-title l-b cds-line-height-100${
          show ? "" : " cds-video-title-with-play-button"
        }`}
        target="_self"
        onMouseOver={() => setShow(true)}
        onFocus={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onBlur={() => setShow(false)}
        href={`/record/${record.id}`}
      >
        <ProgressiveImage
          className="img-responsive"
          gifSrc={getImagePreview(record, true, [400, 224])}
          imgSrc={getImagePreview(record, false, [400, 224])}
        />
        <p>{title(record, 60)}</p>
      </a>
    </div>
  );
}

MediumItem.propTypes = { record: PropTypes.object.isRequired };

/** Search results. */
export function SmallGrid({ results }) {
  return (
    <div className="cds-row cds-search-results">
      {hitsOf(results).map((record, index) => (
        <React.Fragment key={index}>
          <div className="cds-col-md-4 mb-20">
            <a
              className="cds-video-title l-b"
              target="_self"
              href={`/record/${record.id}`}
            >
              <ProgressiveImage
                className="img-responsive"
                gifSrc={getImagePreview(record, true, [330, 190])}
                imgSrc={getImagePreview(record, false, [330, 190])}
              />
              {record.metadata.duration && (
                <span className="cds-video-duration">
                  {record.metadata.duration}
                </span>
              )}
              <p>{title(record, 60)}</p>
            </a>
          </div>
          {!((index + 1) % 3) && <div className="cds-clearfix-md" />}
        </React.Fragment>
      ))}
    </div>
  );
}

SmallGrid.propTypes = { results: PropTypes.object.isRequired };

/** Video cards of the home page sections. */
export function SmallVideoCardGrid({ results }) {
  return (
    <div className="cds-row cds-search-results">
      {hitsOf(results).map((record, index) => (
        <SmallVideoCard key={index} record={record} />
      ))}
    </div>
  );
}

SmallVideoCardGrid.propTypes = { results: PropTypes.object.isRequired };

function SmallVideoCard({ record }) {
  const [show, setShow] = useState(false);
  return (
    <div className="cds-col-md-3">
      <a
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className={`cds-transition cds-video-title l-w cds-line-height-100${
          show ? "" : " cds-video-title-with-play-button"
        }`}
        target="_self"
        href={`/record/${record.id}`}
      >
        <div className="video-thumbnail-wrapper">
          <ProgressiveImage
            gifSrc={getImagePreview(record, true, [400, 220])}
            imgSrc={getImagePreview(record, false, [400, 220])}
          />
        </div>
        <p className="cds-video-title-text">{title(record, 60)}</p>
      </a>
    </div>
  );
}

SmallVideoCard.propTypes = { record: PropTypes.object.isRequired };

export const VIDEO_TEMPLATES = {
  featured: FeaturedVideo,
  "featured-medium": FeaturedMediumGrid,
  medium: MediumGrid,
  small: SmallGrid,
  "small-video-card": SmallVideoCardGrid,
};
