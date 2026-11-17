/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Titles and descriptions of a video in other languages. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { DialogModal } from "@js/cds/shared/components/DialogModal";
import { Tooltip } from "@js/cds/shared/components/Popups";
import { get } from "@js/cds/shared/utils/collections";
import { isoToLanguage } from "@js/cds/shared/utils/languages";

import { TrustedHtml } from "../components/TrustedHtml";
import { sanitize } from "./sanitize";

export function Translations({ record }) {
  const [open, setOpen] = useState(false);
  const translations = get(record, "metadata.translations") || [];
  return (
    <>
      {translations.length > 0 && (
        <Tooltip html="Title and description are available in more languages, please click to see them all.">
          <a
            className="f8"
            href="#translations"
            onClick={(e) => {
              e.preventDefault();
              setOpen(true);
            }}
          >
            <i className="fa fa-info-circle" />
          </a>
        </Tooltip>
      )}
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Available translations"
      >
        {translations.map((translation, index) => (
          <div key={index}>
            <strong>{isoToLanguage(translation.language)}</strong>
            <h4>{get(translation, "title.title")}</h4>
            <TrustedHtml
              as="p"
              html={sanitize(translation.description) || "No description"}
            />
          </div>
        ))}
      </DialogModal>
    </>
  );
}

Translations.propTypes = { record: PropTypes.object.isRequired };
