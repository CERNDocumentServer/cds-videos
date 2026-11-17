/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Dialogs of the uploaders. */

import React from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";
import { prevent } from "@js/cds/shared/dom";

import { useDeposit, useDepositActions } from "../state/hooks";
import { InfoDialog } from "../components/InfoDialog";

export function HowToUpdateDialog() {
  return (
    <InfoDialog
      title="How to update the video file"
      trigger={(open) => (
        <a href="#info" onClick={prevent(open)}>
          <i className="fa fa-info" />
        </a>
      )}
    >
      <p className="text-left">
        To replace the video file, just upload another video file.
      </p>
    </InfoDialog>
  );
}

export function ReplaceMasterDialog({ id, message }) {
  const { newMasterName } = useDeposit(id);
  const { closeNewMasterDialog } = useDepositActions(id);
  return (
    <DialogModal
      open={newMasterName !== null}
      onClose={() => closeNewMasterDialog(false)}
      title="Replace master file"
    >
      <p>{message(newMasterName)}</p>
      <hr className="mt-30 mb-10" />
      <p className="pull-right">
        <button
          type="button"
          className="ui basic button"
          onClick={() => closeNewMasterDialog(false)}
        >
          Cancel
        </button>
        <button
          type="button"
          className="ui green button"
          onClick={() => closeNewMasterDialog(true)}
        >
          Yes
        </button>
      </p>
      <div className="cds-clearfix" />
    </DialogModal>
  );
}

ReplaceMasterDialog.propTypes = {
  id: PropTypes.string.isRequired,
  message: PropTypes.func.isRequired,
};
