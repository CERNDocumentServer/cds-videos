/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Form of a video, with its sidebar and tabs. */

import React from "react";
import PropTypes from "prop-types";

import { show } from "@js/cds/shared/dom";

import { DEPOSIT_STATUSES, urlBuilder } from "../constants";
import { taskRepr } from "../taskStatus";
import {
  useDeposit,
  useDepositActions,
  useDepositStatus,
  useProjectRecord,
} from "../state/hooks";
import { isPublished } from "../state/records";
import { ProgressBar } from "../components/ProgressBar";
import { ErrorAlerts } from "../components/ErrorAlerts";
import { SanitizedHtml } from "../components/SanitizedHtml";
import { VideoPreview } from "../components/VideoPreview";
import { ExtractedMetadata } from "./ExtractedMetadata";
import { VideoSidebar } from "./VideoSidebar";
import { VideoTabs } from "./VideoTabs";

export function VideoForm({ id, onTranscodeInfo }) {
  const { record, showAll, waitingUpload } = useDeposit(id);
  const { changeShowAll } = useDepositActions(id);
  const { status, startedTask } = useDepositStatus(id);
  const master = useProjectRecord();
  const published = isPublished(record);
  const recordUrl = urlBuilder.record({ recid: record.recid });
  const firstFile = (record._files || [])[0] || {};
  return (
    <>
      <ErrorAlerts id={id} />
      <ExtractedMetadata id={id} />
      {/* Hidden, not unmounted: keeps the player preview and the form */}
      <div className="cds-row" style={show(!waitingUpload)}>
        {/* Brief view */}
        {/* Hidden, not unmounted: keeps the player preview loaded */}
        <div style={show(published && !showAll)} className="cds-col-sm-12">
          <div className="cds-row">
            <div className="cds-col-sm-3">
              <VideoPreview id={id} />
            </div>
            <div className="cds-col-sm-9">
              <ul className="cds-list-inline">
                <li>
                  <span className="ui label cds-label cds-label-default">
                    {master.category}
                  </span>
                </li>{" "}
                <li>
                  <span className="ui label cds-label cds-label-warning">
                    {master.type}
                  </span>
                </li>{" "}
                <li>
                  <span className="ui label cds-label cds-label-primary">
                    Published
                  </span>
                </li>
              </ul>
              <hr className="my-15" />
              <h4 className="mb-5 mt-0">
                <a href={recordUrl}>
                  {(record.title && record.title.title) || "No video title"}
                </a>
              </h4>
              <SanitizedHtml html={record.description || "No description"} />
            </div>
          </div>
        </div>
        {/* Detail view */}
        {/* Hidden, not unmounted: keeps the editor and the open tab */}
        <div
          style={show(!published || (published && showAll))}
          className="cds-col-sm-12"
        >
          <div className="cds-row">
            <div className="cds-col-sm-12">
              {status === DEPOSIT_STATUSES.PENDING && (
                <div>
                  <ProgressBar striped active>
                    Loading ...
                  </ProgressBar>
                </div>
              )}
              {status === DEPOSIT_STATUSES.STARTED && (
                <div className="cds-row">
                  <ProgressBar striped active>
                    {taskRepr(startedTask)}
                  </ProgressBar>
                </div>
              )}
              {status === DEPOSIT_STATUSES.SUCCESS &&
                !published &&
                !record.recid && (
                  <div className="cds-row">
                    <ProgressBar success>
                      <strong>Tasks successfully completed!</strong>
                    </ProgressBar>
                  </div>
                )}
            </div>
            <VideoSidebar id={id} onTranscodeInfo={onTranscodeInfo} />
            <VideoTabs id={id} />
          </div>
        </div>
        {published && (
          <div className="cds-row">
            <div className="cds-col-sm-12 text-center">
              <div className="px-20">
                <hr className="mb-15" />
                <button
                  type="button"
                  className="ui small basic button"
                  onClick={() => changeShowAll(showAll)}
                >
                  {showAll ? "Hide details" : "Show details"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      {/* Waiting for the upload */}
      {waitingUpload && (
        <div className="cds-row">
          <div className="cds-col-md-12">
            <div className="cds-progress">
              {Boolean(firstFile.percentage) && (
                <div
                  style={{
                    width: `${firstFile.percentage || 0}%`,
                  }}
                  className="cds-progress-bar cds-progress-bar-primary"
                  role="progressbar"
                >
                  <span className="sr-only">
                    {firstFile.percentage || 0}% Complete
                  </span>
                </div>
              )}
              {!firstFile.percentage && (
                <div
                  style={{ width: "100%" }}
                  className="cds-progress-bar cds-progress-bar-primary cds-progress-bar-striped active"
                  role="progressbar"
                >
                  <span className="sr-only">Loading ...</span>
                  Loading ...
                </div>
              )}
            </div>
            {Boolean(firstFile.percentage) && (
              <p className="text-muted text-center f5">
                {firstFile.percentage || 0}%
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}

VideoForm.propTypes = {
  id: PropTypes.string.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};
