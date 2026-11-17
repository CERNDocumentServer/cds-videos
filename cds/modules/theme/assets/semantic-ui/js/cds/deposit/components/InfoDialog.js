/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";

/** A button opening a dialog. */
export function InfoDialog({ trigger, title, children = null }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      {trigger(() => setOpen(true))}
      <DialogModal open={open} onClose={() => setOpen(false)} title={title}>
        {children}
      </DialogModal>
    </>
  );
}

InfoDialog.propTypes = {
  trigger: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
};
