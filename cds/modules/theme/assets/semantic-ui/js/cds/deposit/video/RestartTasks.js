/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Processing tasks of a video and their restart links. */

import React from "react";
import PropTypes from "prop-types";

import { prevent } from "@js/cds/shared/dom";

import { useDeposit, useDepositActions } from "../state/hooks";
import { isDraft } from "../state/records";

const running = (status) => status === "PENDING" || status === "STARTED";

/** Restart icon of a task, a spinner while it runs. */
function RestartLink({ status, blocked, onRestart }) {
  return (
    <a
      href="#restart"
      className="pull-right"
      style={blocked ? { pointerEvents: "none" } : undefined}
      onClick={prevent(onRestart)}
    >
      {(status === "SUCCESS" || status === "FAILURE") && (
        <i className={`fa fa-refresh ${status}`} aria-hidden="true" />
      )}
      {running(status) && <i className="fa fa-spinner fa-spin" />}
    </a>
  );
}

RestartLink.propTypes = {
  status: PropTypes.string,
  blocked: PropTypes.bool.isRequired,
  onRestart: PropTypes.func.isRequired,
};

export function RestartTasks({ id }) {
  const { record, tasksByName } = useDeposit(id);
  const actions = useDepositActions(id);
  return (
    <div className="cds-panel">
      <div className="cds-panel-heading">
        Restart tasks{" "}
        <a
          href="#restart"
          className="cds-btn-link cds-btn-xs pull-right"
          onClick={prevent(actions.restartFlow)}
        >
          <i className="fa fa-refresh" aria-hidden="true" /> Restart All
        </a>
      </div>
      <div className="cds-panel-body">
        {Object.entries(tasksByName || {}).map(([name, data]) => {
          const first = data[0] || {};
          const payload = (first.info && first.info.payload) || {};
          if (name === "file_transcode") {
            return (
              <ul className="cds-list-group" key={name}>
                <li className="cds-list-group-item">
                  <p>
                    <strong>{name}</strong>
                  </p>
                  <div className="mb-10 text-center">
                    <i className="fa fa-external-link" aria-hidden="true" />{" "}
                    <a
                      href={`/admin/flowmetadata/?search=${payload.flow_id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      See Flow
                    </a>
                    &nbsp;&nbsp;{" "}
                    <i className="fa fa-external-link" aria-hidden="true" />{" "}
                    <a
                      href={`/admin/flowtaskmetadata/?search=${payload.flow_id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      See Tasks
                    </a>
                  </div>
                  {data.map((task, index) => {
                    const taskPayload = (task.info && task.info.payload) || {};
                    const blocked =
                      running(task.status) || task.status === "CANCELLED";
                    return (
                      // eslint-disable-next-line react/no-array-index-key
                      <ul className="cds-list-group" key={index}>
                        <li className="cds-list-group-item">
                          {taskPayload.preset_quality}{" "}
                          <span className="ui label cds-label cds-label-default">
                            {task.status}
                          </span>
                          <RestartLink
                            status={task.status}
                            blocked={blocked}
                            onRestart={() =>
                              !(isDraft(record) || blocked) &&
                              actions.restartTask(
                                taskPayload.flow_id,
                                taskPayload.task_id
                              )
                            }
                          />
                        </li>
                      </ul>
                    );
                  })}
                </li>
              </ul>
            );
          }
          return (
            <ul className="cds-list-group" key={name}>
              <li className="cds-list-group-item">
                <strong>{name}</strong>{" "}
                <span className="ui label cds-label cds-label-default">
                  {first.status}
                </span>
                <RestartLink
                  status={first.status}
                  blocked={running(first.status)}
                  onRestart={() =>
                    first.status !== "PENDING" &&
                    actions.restartTask(payload.flow_id, payload.task_id)
                  }
                />
              </li>
            </ul>
          );
        })}
      </div>
    </div>
  );
}

RestartTasks.propTypes = { id: PropTypes.string.isRequired };
