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
import { Placeholder } from "semantic-ui-react";

import { useDeposit, useDepositStatus } from "../state/hooks";

/**
 * Video preview of a deposit, or the processing spinner. A placeholder
 * covers the player until it has loaded.
 */
export function VideoPreview({ id }) {
  const { previewer } = useDeposit(id);
  const failed = useDepositStatus(id).status === "FAILURE";
  const [loadedSrc, setLoadedSrc] = useState(null);
  const loading = previewer !== null && loadedSrc !== previewer;
  return (
    <div
      className={[
        "cds-deposit-box-video-preview cds-embed-responsive cds-embed-responsive-16by9",
        failed && "preview-failed",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div
        className="cds-deposit-box-video-preview-with-icon"
        style={{ display: previewer ? "none" : undefined }}
      >
        {!failed && <i className="fa fa-spinner fa-spin fa-2x fa-fw" />}
        {failed && <i className="fa fa-remove fa-2x" />}
      </div>
      {previewer !== null && (
        <iframe
          title="Video preview"
          scrolling="no"
          allowFullScreen
          className="cds-embed-responsive-item"
          src={previewer}
          onLoad={() => setLoadedSrc(previewer)}
        />
      )}
      {loading && (
        <Placeholder className="cds-placeholder cds-placeholder-player-loading">
          <Placeholder.Image />
        </Placeholder>
      )}
    </div>
  );
}

VideoPreview.propTypes = { id: PropTypes.string.isRequired };
