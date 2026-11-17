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
 * File selection by click or drag and drop, filtered by a file pattern, a
 * maximum size and a validation function.
 */

import React, { useRef, useState } from "react";
import PropTypes from "prop-types";

const MAX_SIZE = 500 * 1024 * 1024 * 1024; // 500GB

function escapeRegExp(text) {
  return text.replace(/[-[\]/{}()*+?.\\^$|]/g, "\\$&");
}

/** ``ngf-pattern``: file extensions (``.mp4``) or MIME types (``image/*``). */
export function matchesPattern(file, pattern) {
  if (!pattern) {
    return true;
  }
  return pattern
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .some((item) => {
      if (item.indexOf(".") === 0) {
        return new RegExp(escapeRegExp(item) + "$", "i").test(file.name);
      }
      const regexp = new RegExp(
        "^" + escapeRegExp(item).replace(/\\\*/g, ".*") + "$",
        "i"
      );
      return regexp.test(file.type || "");
    });
}

export function DropZone({
  onFiles,
  multiple = false,
  accept = null,
  pattern = null,
  validate = null,
  dragOverClass = "cds-deposit-dragover",
  className = null,
  disabled = false,
  clickable = true,
  droppable = true,
  style = null,
  children = null,
  as: Component = "div",
}) {
  const input = useRef(null);
  const [over, setOver] = useState(false);
  const leaveTimer = useRef(null);

  const handle = (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const valid = [];
    const invalid = [];
    files.forEach((file) => {
      if (
        !matchesPattern(file, pattern) ||
        file.size > MAX_SIZE ||
        (validate && validate(file) === false)
      ) {
        invalid.push(file);
      } else {
        valid.push(file);
      }
    });
    onFiles(multiple ? valid : valid.slice(0, 1), invalid);
  };

  const onDragOver = (event) => {
    if (disabled || !droppable) return;
    event.preventDefault();
    clearTimeout(leaveTimer.current);
    if (!over) setOver(true);
  };

  const onDragLeave = () => {
    clearTimeout(leaveTimer.current);
    leaveTimer.current = setTimeout(() => setOver(false), 100);
  };

  const onDrop = (event) => {
    if (disabled || !droppable) return;
    event.preventDefault();
    setOver(false);
    handle(event.dataTransfer.files);
  };

  const onClick = () => {
    if (!disabled && clickable && input.current) {
      input.current.click();
    }
  };

  const classes = [className, over && dragOverClass].filter(Boolean).join(" ");
  return (
    <Component
      className={classes || undefined}
      style={style || undefined}
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={onClick}
      onKeyDown={(event) => event.key === "Enter" && onClick()}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      {children}
      <input
        ref={input}
        type="file"
        style={{ display: "none" }}
        multiple={multiple}
        accept={accept || undefined}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => {
          handle(event.target.files);
          // Allow selecting the same file again
          // eslint-disable-next-line no-param-reassign
          event.target.value = "";
        }}
      />
    </Component>
  );
}

DropZone.propTypes = {
  onFiles: PropTypes.func.isRequired,
  multiple: PropTypes.bool,
  accept: PropTypes.string,
  pattern: PropTypes.string,
  validate: PropTypes.func,
  dragOverClass: PropTypes.string,
  className: PropTypes.string,
  disabled: PropTypes.bool,
  clickable: PropTypes.bool,
  droppable: PropTypes.bool,
  style: PropTypes.object,
  children: PropTypes.node,
  as: PropTypes.elementType,
};
