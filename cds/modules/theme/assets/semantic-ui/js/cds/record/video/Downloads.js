/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Downloads of a video: its formats, thumbnails and other files. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { Popover } from "@js/cds/shared/components/Popups";
import { get, groupBy } from "@js/cds/shared/utils/collections";
import {
  findFrames,
  findMaster,
  findResolution,
  getAllFilesExcept,
  getFilesByType,
  groupDownloadable,
  sortVideosDescending,
} from "@js/cds/shared/utils/records";
import {
  bytesToHumanReadable,
  middleEllipsis,
} from "@js/cds/shared/utils/text";
import { download } from "@js/cds/shared/utils/urls";
import { isoToLanguage } from "@js/cds/shared/utils/languages";

const BIG_FILE_WARNING =
  "<strong>Warning: Big file!</strong><br>As no network or browser is 100% stable, we <em>strongly</em> recommend using a download manager.";

function Checksum({ checksum = "" }) {
  return (
    <Popover title="md5 checksum" content={checksum}>
      <a
        className="download-list-item-checksum"
        title="md5 checksum"
        href="#checksum"
        onClick={(e) => e.preventDefault()}
      >
        checksum
      </a>
    </Popover>
  );
}

Checksum.propTypes = { checksum: PropTypes.string };

function DownloadItem({ file, label = null, onDownload }) {
  return (
    <div className="download-list-item">
      <span>
        {label} <span className="download-list-fade">|</span>{" "}
        {bytesToHumanReadable(file.size)}
      </span>
      <div className="download-list-item-container">
        <Checksum checksum={file.checksum} />
        <a
          className="ui basic button download-list-item-button"
          href={download(get(file, "links.self"))}
          onClick={() => onDownload(file)}
          target="_blank"
          rel="noreferrer"
        >
          Download
        </a>
      </div>
    </div>
  );
}

DownloadItem.propTypes = {
  file: PropTypes.object.isRequired,
  label: PropTypes.node,
  onDownload: PropTypes.func.isRequired,
};

/** Collapsible section ("Other video formats", "Thumbnails", ...). */
function Toggle({ title, open, onToggle, className = null }) {
  return (
    <div className="cds-row">
      <div className="cds-col-md-12">
        <a
          className={`f8 display-block${className ? " " + className : ""}`}
          onClick={(e) => {
            e.preventDefault();
            onToggle();
          }}
          href="#toggle"
        >
          {title}
          <p className="pull-right mb-0">
            <span>
              <i
                className={`fa f5 ${open ? "fa-angle-up" : "fa-angle-down"}`}
              />
            </span>
          </p>
        </a>
      </div>
    </div>
  );
}

Toggle.propTypes = {
  title: PropTypes.string.isRequired,
  open: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  className: PropTypes.string,
};

function FileLinks({ files, show, label }) {
  return (
    <div
      className="cds-detail-download-box cds-detail-video-download-box mt-5"
      style={{ display: show ? undefined : "none" }}
    >
      <div className="list-group">
        {files.map((file, index) => (
          <a
            key={index}
            title={file.key}
            className="download-list-item-other"
            href={download(get(file, "links.self"))}
            style={{
              display: file.context_type === "master" ? "none" : undefined,
            }}
            target="_blank"
            rel="noreferrer"
          >
            {label(file)}
            <span className="pull-right">
              <small>{bytesToHumanReadable(file.size)}</small>
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}

FileLinks.propTypes = {
  files: PropTypes.array.isRequired,
  show: PropTypes.bool.isRequired,
  label: PropTypes.func.isRequired,
};

export function Downloads({ record, onDownload }) {
  const [showAllOtherFiles, setShowAllOtherFiles] = useState(false);
  const [showAllFrames, setShowAllFrames] = useState(false);
  const [showSubtitles, setShowSubtitles] = useState(false);
  const [showAdditionalVideos, setShowAdditionalVideos] = useState(false);
  const [showOtherFiles, setShowOtherFiles] = useState(false);

  const master = findMaster(record) || {};
  const subformats = groupDownloadable(master.subformat);
  const downloadable = subformats.download || [];
  const additional = subformats.additional || [];
  const frames = findFrames(record);
  const files = get(record, "metadata._files");
  const allFilesShown = (files || []).length > 1;
  const subtitles = getFilesByType(files, ["subtitle"]) || [];
  const videos = getFilesByType(files, ["video"]) || [];
  const others = getAllFilesExcept(files, ["subtitle", "video"]) || [];

  return (
    <>
      {/* Download */}
      <div className="cds-detail-title cds-detail-video-title">
        <h3 className="cds-title-section-decoration bt bw-1 pt-10 mb-0">
          <i className="fa fa-download" /> Download
        </h3>
        <p className="cds-detail-video-subtitle">
          By downloading any of these files you accept{" "}
          <a
            href="http://copyright.web.cern.ch/"
            className="cds-detail-video-link"
            target="_blank"
            rel="noreferrer"
          >
            CERN&apos;s Terms of Use
          </a>
        </p>
      </div>

      {/* Subformat */}
      {master.key && (
        <div className="cds-video-subformats pb-20">
          <div
            className="cds-detail-download-box cds-detail-video-download-box"
            style={{ display: downloadable.length > 0 ? undefined : "none" }}
          >
            <div className="download-list-wrapper">
              {Object.entries(groupBy(downloadable, "tags.type", "others")).map(
                ([type, subs]) => (
                  <div key={type}>
                    <div className="download-list-container">
                      <p className="mt-10 tw-b text-uppercase text-muted">
                        {type}
                      </p>
                      <div className="download-list-group">
                        {subs.map((file, index) => (
                          <DownloadItem
                            key={index}
                            file={file}
                            label={get(file, "tags.preset_quality")}
                            onDownload={onDownload}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
          {/* Master file */}
          <div className="download-list-container">
            <div className="download-list-header">
              <p className="mt-10 tw-b text-uppercase text-muted">
                for broadcasters
              </p>
              {master.size > 1e8 && (
                <Popover html={BIG_FILE_WARNING}>
                  <a
                    className="download-list-header-warning"
                    href="#warning"
                    onClick={(e) => e.preventDefault()}
                  >
                    <i className="fa fa-info-circle" />
                  </a>
                </Popover>
              )}
            </div>
            <div className="download-list-group">
              <DownloadItem
                file={master}
                label={findResolution(master)}
                onDownload={onDownload}
              />
            </div>
          </div>
        </div>
      )}
      {!master.key && (
        <div className="cds-video-subformats">
          <p className="text-muted text-center">No master file available.</p>
        </div>
      )}

      {/* Other formats */}
      <div
        className="cds-video-subformats bt bw-1 bc-gl pt-10 pb-10"
        style={{ display: additional.length > 0 ? undefined : "none" }}
      >
        <Toggle
          title="Other video formats"
          className="mt-5"
          open={showAllOtherFiles}
          onToggle={() => setShowAllOtherFiles(!showAllOtherFiles)}
        />
        <div
          className="cds-detail-download-box cds-detail-video-download-box mt-5"
          style={{
            display:
              additional.length > 0 && showAllOtherFiles ? undefined : "none",
          }}
        >
          <div>
            {sortVideosDescending(additional).map((file, index) => (
              <DownloadItem
                key={index}
                file={file}
                label={get(file, "tags.preset_quality")}
                onDownload={onDownload}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Frame */}
      {frames.length > 0 && (
        <div className="cds-video-subformats bt bw-1 bc-gl pt-10 pb-10">
          <Toggle
            title="Thumbnails"
            open={showAllFrames}
            onToggle={() => setShowAllFrames(!showAllFrames)}
          />
          <div
            className="cds-detail-download-box cds-detail-video-download-box  mt-5"
            style={{ display: showAllFrames ? undefined : "none" }}
          >
            <div className="list-group">
              {frames.map((file, index) => (
                <a
                  key={index}
                  className="download-list-item-other"
                  href={download(get(file, "links.self"))}
                  target="_blank"
                  rel="noreferrer"
                >
                  {file.key}
                  <span className="pull-right">
                    <small>{bytesToHumanReadable(file.size)}</small>
                  </span>
                </a>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Subtitles */}
      {subtitles.length > 0 && (
        <div className="cds-video-subformats bt bw-1 bc-gl pt-10 pb-10">
          <Toggle
            title="Subtitles"
            open={showSubtitles}
            onToggle={() => setShowSubtitles(!showSubtitles)}
          />
          <FileLinks
            files={subtitles}
            show={allFilesShown && showSubtitles}
            label={(file) => isoToLanguage(get(file, "tags.language"))}
          />
        </div>
      )}

      {/* Additional video files */}
      {videos.length > 1 && (
        <div className="cds-video-subformats bt bw-1 bc-gl pt-10 pb-10">
          <Toggle
            title="Additional video files"
            open={showAdditionalVideos}
            onToggle={() => setShowAdditionalVideos(!showAdditionalVideos)}
          />
          <FileLinks
            files={videos}
            show={allFilesShown && showAdditionalVideos}
            label={(file) => middleEllipsis(file.key, 25)}
          />
        </div>
      )}

      {/* Other files */}
      {others.length > 0 && (
        <div className="cds-video-subformats bt bw-1 bc-gl pt-10 pb-10">
          <Toggle
            title="Other files"
            open={showOtherFiles}
            onToggle={() => setShowOtherFiles(!showOtherFiles)}
          />
          <FileLinks
            files={others}
            show={allFilesShown && showOtherFiles}
            label={(file) => middleEllipsis(file.key, 25)}
          />
        </div>
      )}
    </>
  );
}

Downloads.propTypes = {
  record: PropTypes.object.isRequired,
  onDownload: PropTypes.func.isRequired,
};
