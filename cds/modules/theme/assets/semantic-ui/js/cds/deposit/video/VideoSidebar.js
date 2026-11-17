/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/**
 * Sidebar of the video form, with the button inheriting the project
 * metadata.
 */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";
import { prevent } from "@js/cds/shared/dom";

import { urlBuilder } from "../constants";
import {
  useConfig,
  useDeposit,
  useDepositActions,
  useProjectRecord,
} from "../state/hooks";
import { isPublished } from "../state/records";
import { TaskList } from "../components/TaskList";
import { VideoPreview } from "../components/VideoPreview";

/* Sidebar of the detail view */

function InheritButton({ id }) {
  const { record } = useDeposit(id);
  const { inheritMetadata } = useDepositActions(id);
  const project = useProjectRecord();
  const [open, setOpen] = useState(false);
  return project.title && !isPublished(record) ? (
    <div>
      <hr className="mt-10 mb-20" />
      <div className="text-center">
        <button
          type="button"
          className="ui small button cds-btn-info"
          onClick={() => setOpen(true)}
        >
          Inherit metadata from project
        </button>
      </div>
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Inherit metadata from the project"
        buttons={[
          ["Only the missing fields", "basic", () => inheritMetadata(false)],
          ["Replace all metadata", "basic", () => inheritMetadata(true)],
        ]}
      >
        <p className="text-left">
          Please select if you would like to replace all metadata of this video
          or inherit only the missing metadata from the project.
        </p>
      </DialogModal>
    </div>
  ) : null;
}

InheritButton.propTypes = { id: PropTypes.string.isRequired };

export function VideoSidebar({ id, onTranscodeInfo }) {
  const { record } = useDeposit(id);
  const { showAvcRestrictedFields } = useConfig();
  const master = useProjectRecord();
  const published = isPublished(record);
  const recordUrl = urlBuilder.record({ recid: record.recid });
  return (
    <div className="cds-col-sm-3">
      <VideoPreview id={id} />
      <div>
        {master.category && (
          <div className="text-muted mt-10">
            <div className="cds-row">
              <div className="cds-col-md-6">
                <p className="mb-0">Category</p>
                <p>
                  <span className="ui label cds-label cds-label-default">
                    {master.category}
                  </span>
                </p>
              </div>
              <div className="cds-col-md-6">
                <p className="mb-0">Type</p>
                {master.type && (
                  <p>
                    <span className="ui label cds-label cds-label-warning">
                      {master.type}
                    </span>
                  </p>
                )}
              </div>
            </div>
            <hr className="my-10" />
          </div>
        )}
        {!master.category && (
          <div className="text-muted mt-10">
            <i className="fa fa-info-circle" /> For publishing the video{" "}
            {showAvcRestrictedFields && (
              <span>, or assigning a report number, </span>
            )}{" "}
            please select category and type from the{" "}
            <a
              href={`#${master._deposit.id}`}
              onClick={prevent(() =>
                document
                  .getElementById(master._deposit.id)
                  ?.scrollIntoView({ behavior: "smooth" })
              )}
            >
              Project
            </a>
            .
            <hr className="my-10" />
          </div>
        )}
        <p className="text-muted mb-0">
          <strong>Video status:</strong>
        </p>
        {published && (
          <div>
            <p className="text-muted mb-0">
              <span className="ui label cds-label cds-label-primary">
                Published
              </span>
            </p>
            <hr className="my-10" />
            <p className="mt-10">
              <i className="fa text-muted fa-link" />{" "}
              <a href={recordUrl}>Visit video page</a>
            </p>
          </div>
        )}
        {!published && (
          <div className="text-muted">
            <p>
              The video is <strong>not</strong> published.
            </p>
            <ul className="list-unstyled text-left my">
              <TaskList
                state={record._cds && record._cds.state}
                small
                onTranscodeInfo={onTranscodeInfo}
              />
            </ul>
          </div>
        )}
        <InheritButton id={id} />
      </div>
    </div>
  );
}

VideoSidebar.propTypes = {
  id: PropTypes.string.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};
