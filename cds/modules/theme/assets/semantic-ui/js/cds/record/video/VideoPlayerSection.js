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

import { get } from "@js/cds/shared/utils/collections";
import { previewIframeSrc } from "@js/cds/shared/utils/urls";

import { PlayerFrame } from "./PlayerFrame";

/**
 * The player of a video. ``children`` is the "In this video" panel, next to
 * the player when ``withPanel``.
 */
export function VideoPlayerSection({
  metadata,
  master,
  panelOpen,
  withPanel,
  children = null,
}) {
  return (
    <div
      className={`video-section${panelOpen ? " cds-container-fluid" : ""}`}
      id="videoPlayerSection"
    >
      <div className={withPanel ? "cds-row" : undefined}>
        <div className={withPanel ? "cds-col-md-8 pt-20" : undefined}>
          <div className="cds-video-iframe text-center">
            <PlayerFrame
              title={get(metadata, "title.title") || "Video"}
              src={previewIframeSrc(metadata.recid, master.key)}
            />
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

VideoPlayerSection.propTypes = {
  metadata: PropTypes.object.isRequired,
  master: PropTypes.object.isRequired,
  panelOpen: PropTypes.bool.isRequired,
  withPanel: PropTypes.bool.isRequired,
  children: PropTypes.node,
};
