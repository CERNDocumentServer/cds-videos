/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React from "react";
import PropTypes from "prop-types";

/** Invitation to open the transcripts of a video, when it has some. */
export function TranscriptsTeaser({ visible, onShow }) {
  return (
    <div className="mb-20" style={{ display: visible ? undefined : "none" }}>
      <hr />
      <div className="transcription-text">
        <h3>
          <strong>Transcriptions</strong>
        </h3>
        <small className="text-muted">
          Follow along or search within the transcript.
        </small>
      </div>
      <div className="transcription-button-wrapper pt-10">
        <button
          type="button"
          className="ui small basic button transcription-button"
          onClick={onShow}
        >
          Show Transcriptions
        </button>
      </div>
    </div>
  );
}

TranscriptsTeaser.propTypes = {
  visible: PropTypes.bool.isRequired,
  onShow: PropTypes.func.isRequired,
};
