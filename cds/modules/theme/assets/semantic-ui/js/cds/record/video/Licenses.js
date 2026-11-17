/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Licenses of a video that are not CERN ones. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";
import { Tooltip } from "@js/cds/shared/components/Popups";

const UNKNOWN_LICENSE_TEXT =
  "This resource is copyrighted as non-CERN and unfortunately we don't have enough information about its licence. None of CERN's terms of use will apply. Please contact the copyright holder directly for more information.";

function UnknownLicense({ label, title }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <a
        href="#licence"
        onClick={(e) => {
          e.preventDefault();
          setOpen(true);
        }}
      >
        {label}
      </a>
      <DialogModal open={open} onClose={() => setOpen(false)} title={title}>
        <div>
          <p>{UNKNOWN_LICENSE_TEXT}</p>
        </div>
      </DialogModal>
    </>
  );
}

UnknownLicense.propTypes = {
  label: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
};

/** Licence of the video in the date bar (``material == 'other'``). */
export function OtherLicense({ licenses }) {
  const license = licenses[0].license;
  let content;
  if (!license) {
    content = <UnknownLicense label="Unknown" title="Unknown" />;
  } else if (license === "CERN") {
    content = (
      <a target="_blank" rel="noreferrer" href="http://copyright.web.cern.ch/">
        Conditions of Use
      </a>
    );
  } else if (license === "unknown") {
    content = (
      <UnknownLicense label="Unknown Licence" title="Unknown Licence" />
    );
  } else if (licenses[0].url) {
    content = (
      <a target="_blank" rel="noreferrer" href={licenses[0].url}>
        {license}
      </a>
    );
  } else {
    content = <span>{license}</span>;
  }
  return (
    <Tooltip html="License">
      <li>
        <i className="fa fa-certificate text-muted" /> <span>{content}</span>
      </li>
    </Tooltip>
  );
}

OtherLicense.propTypes = { licenses: PropTypes.array.isRequired };
