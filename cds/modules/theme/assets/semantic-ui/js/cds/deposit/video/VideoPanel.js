/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/*
 * A video of the project: its actions and its form.
 */

import React from "react";
import PropTypes from "prop-types";

import { useConfig, useDeposit } from "../state/hooks";
import { DepositForm } from "../fields/DepositForm";
import { VideoActions } from "./VideoActions";
import { VideoForm } from "./VideoForm";

export function VideoPanel({ id, index, onTranscodeInfo }) {
  const reportNumber = useDeposit(id).record.report_number;
  const { maxNumberOfVideos } = useConfig();
  return (
    <div id={id}>
      <div id={`video_${id}`} className="cds-deposit-panel cds-panel">
        <div className="cds-panel-heading text-muted px-20 py-10 cds-sticky-heading">
          <span className="text-muted">
            <i className="fa fa-video-camera" /> Video #{index + 1} (of{" "}
            {maxNumberOfVideos}){" "}
            {reportNumber && (
              <span className="ui label cds-label cds-label-primary ml-10">
                {" "}
                {reportNumber[0]}{" "}
              </span>
            )}
          </span>
          <span className="pull-right">
            <VideoActions id={id} />
          </span>
        </div>
        <div className="cds-panel-body">
          <DepositForm id={id}>
            <VideoForm id={id} onTranscodeInfo={onTranscodeInfo} />
          </DepositForm>
        </div>
      </div>
    </div>
  );
}

VideoPanel.propTypes = {
  id: PropTypes.string.isRequired,
  index: PropTypes.number.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};
