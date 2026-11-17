/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Action buttons of a video, such as publish and delete. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";

import { DEPOSIT_STATUSES } from "../constants";
import {
  useConfig,
  useDeposit,
  useDepositActions,
  useDepositStatus,
  useLoading,
  useProjectRecord,
} from "../state/hooks";
import { findMasterFile, isDraft, isPublished } from "../state/records";

export function VideoActions({ id }) {
  const deposit = useDeposit(id);
  const actions = useDepositActions(id);
  const { showAvcRestrictedFields } = useConfig();
  const project = useProjectRecord();
  const loading = useLoading();
  const [deleteShown, setDeleteShown] = useState(false);
  const [publishShown, setPublishShown] = useState(false);
  const [cannotEditShown, setCannotEditShown] = useState(false);
  const { record, framesReady } = deposit;
  const actionLoading = deposit.pending > 0;
  const success = useDepositStatus(id).status === DEPOSIT_STATUSES.SUCCESS;
  const published = isPublished(record);
  const masterFile = findMasterFile(record) || {};
  const showAssign =
    !record.report_number &&
    showAvcRestrictedFields &&
    project.category &&
    project.type;

  // Same as the button at the bottom of the form, which can be far below.
  // Back to the top of the video when it was scrolled out of view.
  const hideDetails = () => {
    actions.changeShowAll(true);
    const panel = document.getElementById(id);
    if (panel && panel.getBoundingClientRect().top < 0) {
      panel.scrollIntoView({ behavior: "smooth" });
    }
  };

  return !deposit.waitingUpload ? (
    <div>
      <DialogModal
        open={deleteShown}
        onClose={() => setDeleteShown(false)}
        title="Delete video"
        buttons={[
          ["Yes", "green", actions.remove],
          ["No", "red"],
        ]}
      >
        Are you sure you want permanently delete the video?
      </DialogModal>
      <DialogModal
        open={publishShown}
        onClose={() => setPublishShown(false)}
        title="Publish video"
        buttons={[
          ["No", "basic"],
          ["Yes", "green", actions.publishVideo],
        ]}
      >
        The video workflow is still processing.
        <br />
        <br />
        You can publish the video even if not all video subformats have been
        generated yet.
        <br />
        Before publishing the video, make sure that at least on subformats has
        been completed by checking the &quot;Files&quot; tab.
        <br />
        Completed video subformats will be automatically published.
        <br />
        <br />
        Do you want publish the video?
        <br />
      </DialogModal>
      <DialogModal
        open={cannotEditShown}
        onClose={() => setCannotEditShown(false)}
        title="Cannot edit the video"
        buttons={[["Close", "primary"]]}
      >
        You cannot edit the video if the project is published.
        <br />
        Please <strong>edit the project first</strong>, and then edit the video.
        <br />
      </DialogModal>
      <div className="text-right">
        {loading && (
          <span>
            <i className="fa fa-spinner fa-spin text-muted fa-fw" />
          </span>
        )}{" "}
        {published && deposit.showAll && (
          <>
            <button
              type="button"
              className="ui small basic button"
              onClick={hideDetails}
            >
              Hide details
            </button>{" "}
          </>
        )}
        {!(record._deposit.status === "published" || record._deposit.pid) && (
          <>
            <button
              type="button"
              className="ui small basic button"
              disabled={
                (!framesReady || loading) && !(masterFile.size === undefined)
              }
              onClick={() => setDeleteShown(true)}
            >
              <i className="fa fa-trash-o" />
            </button>{" "}
          </>
        )}
        {!published && (
          <>
            <button
              type="button"
              className="ui small green button"
              disabled={!deposit.dirty || loading}
              onClick={() => actions.run("SAVE_PARTIAL")}
            >
              {actionLoading ? "Saving ..." : "Save"}
            </button>{" "}
            <button
              type="button"
              className="ui small primary button"
              disabled={!framesReady || loading}
              // Still processing: confirm first
              onClick={
                success ? actions.publishVideo : () => setPublishShown(true)
              }
            >
              {actionLoading ? "Publishing ..." : "Publish"}
            </button>{" "}
          </>
        )}
        {!isDraft(record) && (
          <>
            <button
              type="button"
              className="ui small basic button"
              disabled={loading}
              onClick={() =>
                actions.editPublished(() => setCannotEditShown(true))
              }
            >
              {actionLoading ? "Editing ..." : "Edit"}
            </button>{" "}
          </>
        )}
        {showAssign && (
          <a
            className={`ui small orange button${loading ? " disabled" : ""}`}
            href={`/deposit/reportnumbers/assign/${id}`}
          >
            Assign Report Number
          </a>
        )}
      </div>
    </div>
  ) : null;
}

VideoActions.propTypes = { id: PropTypes.string.isRequired };
