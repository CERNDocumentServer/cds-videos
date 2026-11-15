/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Small parts shared by the deposit views. */

import React, { useState } from "react";
import PropTypes from "prop-types";
import DOMPurify from "dompurify";
import { Placeholder } from "semantic-ui-react";

import { DialogModal } from "@js/cds/components/DialogModal";

import { orderTasks, progressClass, progressIcon, taskRepr } from "../filters";
import {
  useDeposit,
  useDepositActions,
  useDepositStatus,
} from "../state/hooks";

/** Style hiding an element, like ``ng-show``. */
export function show(condition) {
  return { display: condition ? undefined : "none" };
}

/** Bootstrap like panel (``panel panel-default``). */
export function Panel({
  className = null,
  heading = null,
  headingClassName = null,
  children = null,
  bodyClassName = null,
  id = undefined,
}) {
  return (
    <div id={id} className={["cds-panel", className].filter(Boolean).join(" ")}>
      {heading !== null && (
        <div
          className={["cds-panel-heading", headingClassName]
            .filter(Boolean)
            .join(" ")}
        >
          {heading}
        </div>
      )}
      {children !== null && (
        <div
          className={["cds-panel-body", bodyClassName]
            .filter(Boolean)
            .join(" ")}
        >
          {children}
        </div>
      )}
    </div>
  );
}

Panel.propTypes = {
  className: PropTypes.string,
  heading: PropTypes.node,
  headingClassName: PropTypes.string,
  children: PropTypes.node,
  bodyClassName: PropTypes.string,
  id: PropTypes.string,
};

/** Bootstrap like progress bar. */
export function ProgressBar({
  striped = false,
  active = false,
  success = false,
  width = 100,
  children = null,
}) {
  return (
    <div className="cds-progress">
      <div
        className={[
          "cds-progress-bar",
          striped && "cds-progress-bar-striped",
          active && "active",
          success && "cds-progress-bar-success",
        ]
          .filter(Boolean)
          .join(" ")}
        role="progressbar"
        style={{ width: `${width}%` }}
      >
        {children}
      </div>
    </div>
  );
}

ProgressBar.propTypes = {
  striped: PropTypes.bool,
  active: PropTypes.bool,
  success: PropTypes.bool,
  width: PropTypes.number,
  children: PropTypes.node,
};

/** Bootstrap like tabs. */
export function Tabs({ active, onChange, tabs }) {
  return (
    <div className="ui tabular menu cds-nav-tabs" role="tablist">
      {tabs
        .filter((tab) => !tab.hidden)
        .map((tab) => (
          <a
            key={tab.key}
            href={`#${tab.key}`}
            role="tab"
            className={`item${active === tab.key ? " active" : ""}`}
            onClick={(e) => {
              e.preventDefault();
              onChange(tab.key);
            }}
          >
            {tab.title}
          </a>
        ))}
    </div>
  );
}

Tabs.propTypes = {
  active: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  tabs: PropTypes.array.isRequired,
};

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
    // No whitespace between the items, as with ``ng-repeat``
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

/** Validation errors returned by the server (``alert alert-danger``). */
export function ErrorAlerts({ id }) {
  const { alerts } = useDeposit(id);
  const { dismissAlert } = useDepositActions(id);
  return alerts.map((alert, index) => (
    // eslint-disable-next-line react/no-array-index-key
    <div className="alerts" key={index}>
      {alert.errors && alert.errors.length > 0 && alert.type === "danger" && (
        <div>
          <div
            className="cds-alert cds-alert-danger cds-alert-dismissible"
            role="alert"
          >
            <button
              type="button"
              className="cds-close"
              onClick={() => dismissAlert(index)}
            >
              <span aria-hidden="true">&times;</span>
              <span className="sr-only">Close</span>
            </button>
            <div>
              <strong>{alert.message}</strong>
              <ul>
                {alert.errors.map((error, errorIndex) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <li key={errorIndex}>
                    <b>{error.field}</b> {error.message}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  ));
}

ErrorAlerts.propTypes = { id: PropTypes.string.isRequired };

/** Trusted HTML of the record, sanitized. */
export function Html({ html = "", as: Component = "p", className = null }) {
  return (
    <Component
      className={className || undefined}
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html || "") }}
    />
  );
}

Html.propTypes = {
  html: PropTypes.string,
  as: PropTypes.elementType,
  className: PropTypes.string,
};

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
