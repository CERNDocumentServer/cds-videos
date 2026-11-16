/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* static/templates/cds_records/project/detail.html */

import React, { useState } from "react";
import PropTypes from "prop-types";
import DOMPurify from "dompurify";

import { CopyButton } from "@js/cds/components/CopyButton";
import { ellipsis, get, iiif, NOT_FOUND_IMAGE } from "@js/cds/utils";

import { DoiBadge, Html, Keywords, ReportNumberBadge } from "../common";

function VideoItem({ video }) {
  const [gif, setGif] = useState(false);
  return (
    <div className="cds-col-md-4">
      <a
        className="cds-video-title l-b"
        target="_self"
        href={`/record/${video.recid}`}
      >
        <img
          className="img-responsive"
          src={iiif(video, gif, [330, 190])}
          alt=""
          onMouseOver={() => setGif(true)}
          onFocus={() => setGif(true)}
          onMouseLeave={() => setGif(false)}
          onError={(e) => {
            if (e.target.getAttribute("src") !== NOT_FOUND_IMAGE) {
              e.target.setAttribute("src", NOT_FOUND_IMAGE);
            }
          }}
        />
        {video.duration && (
          <span className="cds-video-duration">{video.duration}</span>
        )}
        <p>{ellipsis(get(video, "title.title") || "No title", 120)}</p>
      </a>
    </div>
  );
}

VideoItem.propTypes = { video: PropTypes.object.isRequired };

export function ProjectDetail({ record }) {
  const metadata = record.metadata;
  const translations = metadata.translations || [];
  return (
    <div className="cds-detail-video cds-detail-video-wrapper bg-n pb-20">
      {/* Metadata Section */}
      <div className="cds-container">
        <div className="cds-row">
          <div className="cds-col-md-12">
            <div className="cds-detail cds-detail-video cds-div-shadow bg-w pt-10 px-20 pb-20 mt-30">
              {/* DOI and report number */}
              <div className="cds-row">
                <div className="cds-col-md-4">
                  <ul
                    className="cds-list-inline"
                    style={{
                      display: get(record, "links.project_edit")
                        ? undefined
                        : "none",
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
                <div className="cds-col-md-8">
                  <ul className="cds-list-inline text-right">
                    {metadata.doi && (
                      <li>
                        <DoiBadge record={record} />
                      </li>
                    )}{" "}
                    {get(metadata, "report_number[0]") && (
                      <li className="pr-0">
                        <ReportNumberBadge record={record} />
                      </li>
                    )}{" "}
                  </ul>
                </div>
              </div>
              {/* Title */}
              <div className="cds-detail-title cds-detail-video-title">
                <hgroup>
                  <h1 className="mb-0 f4 fw-n t-b">
                    {get(metadata, "title.title")}
                  </h1>
                  {translations.length > 0 && (
                    <h2 className="mb-0 mt-0 fw-n t-b f5 text-muted text-italic">
                      <em>{get(translations[0], "title.title")}</em>
                    </h2>
                  )}
                </hgroup>
              </div>
              {/* Description */}
              <hr />
              <div className="cds-detail-description cds-detail-video-description t-b">
                <Html
                  as="p"
                  className="f7 mb-20"
                  html={
                    DOMPurify.sanitize(metadata.description || "", {
                      ADD_ATTR: ["target"],
                    }) || "No description"
                  }
                />
              </div>
              {/* More */}
              <div className="cds-detail-more cds-detail-video-more">
                <div className="cds-row">
                  <div className="cds-col-md-12 text-center">
                    <h2 className="mb-20 fw-b f4">Videos</h2>
                  </div>
                  {(metadata.videos || []).map((video, index) => (
                    <VideoItem key={index} video={video} />
                  ))}
                </div>
              </div>
              <div className="cds-detail-more cds-detail-video-more">
                <Keywords record={record} />
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="cds-container">
        <div className="cds-row">
          <div className="cds-col-sm-12">
            {/* EOS (only if the user has access) */}
            {metadata._eos_library_path && (
              <div className="cds-detail cds-detail-video cds-div-shadow bg-gl bt bw-1 bc-ccc pt-10 pb-20 px-20">
                <div className="cds-detail-title cds-detail-video-title">
                  <h3 className="cds-title-section-decoration bt bw-1 pt-10 mb-20">
                    <i className="fa fa-folder-open" /> EOS path to library
                  </h3>
                </div>
                <div className="cds-detail-video-embed">
                  <div className="ui fluid action input cds-input-group">
                    <input
                      id="copyEmbed"
                      type="text"
                      className="bg-w"
                      value={metadata._eos_library_path}
                      readOnly
                    />
                    <CopyButton targetId="copyEmbed" />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

ProjectDetail.propTypes = { record: PropTypes.object.isRequired };
