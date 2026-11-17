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

import {
  orderTasks,
  progressClass,
  progressIcon,
  taskRepr,
} from "../taskStatus";

/** Tasks of a deposit with their status icons. */
export function TaskList({
  state = {},
  small = false,
  onTranscodeInfo,
  itemClassName = null,
}) {
  return orderTasks(state).map(([task, status]) => {
    const content = (
      <>
        <i
          className={`fa fa-fw ${progressIcon(status)} ${progressClass(
            status
          )}`}
        />{" "}
        {taskRepr(task)}{" "}
        <a
          href="#help"
          onClick={(e) => {
            e.preventDefault();
            onTranscodeInfo();
          }}
        >
          {task === "file_transcode" && <i className="fa fa-info-circle" />}
        </a>
      </>
    );
    // No whitespace between the items, as in the previous interface
    return (
      <li key={task} className={itemClassName || undefined}>
        {small ? <small>{content}</small> : content}
      </li>
    );
  });
}

TaskList.propTypes = {
  state: PropTypes.object,
  small: PropTypes.bool,
  onTranscodeInfo: PropTypes.func.isRequired,
  itemClassName: PropTypes.string,
};
