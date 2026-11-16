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
 * The list of the deposits (cds_deposit/index.html): search bar
 * (invenio_deposit/searchbar.html) and results (cds_deposit/search/results.html).
 */

import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Placeholder } from "semantic-ui-react";

import { useSearch } from "@js/cds/search/hooks";
import { formatDate, wordsSplit } from "@js/cds/utils";

import {
  orderTasks,
  overallState,
  progressClass,
  progressIcon,
  taskRepr,
} from "../filters";

/** Search bar of the deposits (``invenio_deposit/searchbar.html``). */
export function DepositSearchBar({ placeholder }) {
  const [state, store] = useSearch();
  const query = state.currentParams.q || "";
  const [userQuery, setUserQuery] = useState(query);
  useEffect(() => setUserQuery(query), [query]);
  const updateQuery = () => store.changeParams({ q: userQuery });
  return (
    <form
      className="form"
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        updateQuery();
      }}
    >
      <div className="form-group">
        <div className="ui fluid action input cds-input-group">
          <input
            type="text"
            className="cds-form-control"
            placeholder={placeholder}
            value={userQuery}
            onChange={(e) => setUserQuery(e.target.value)}
          />
          <button type="submit" className="ui basic button">
            <i className="fa fa-search" />
          </button>
        </div>
      </div>
    </form>
  );
}

DepositSearchBar.propTypes = { placeholder: PropTypes.string };

DepositSearchBar.defaultProps = { placeholder: "" };

const STATE_CLASSES = {
  // As before, the overall state is never prefixed, so only the published
  // deposits get a class
  "DEPOSIT_STATE/FAILURE": "cds-tasks-error",
  "DEPOSIT_STATE/SUCCESS": "cds-tasks-success",
  "DEPOSIT_STATE/PENDING": "cds-tasks-pending",
  "DEPOSIT_STATE/STARTED": "cds-tasks-started",
};

function DepositItem({ record }) {
  const metadata = record.metadata;
  const state = overallState(metadata._cds && metadata._cds.state);
  const status = metadata._deposit.status;
  const classes = [
    "media mb-10 pa-5 cds-deposit-media-list-border",
    status === "draft" && STATE_CLASSES[state],
    status === "published" && "cds-deposit-published",
  ]
    .filter(Boolean)
    .join(" ");
  const videos = metadata.videos || [];
  return (
    <ul className="cds-deposit-media-list media-list">
      <li id={`depoost_${metadata._deposit.id}`} className={classes}>
        <div className="media-left">
          <i
            className={`fa pl-5 ${progressIcon(state)} ${progressClass(state)}`}
          />
        </div>
        <div className="media-body">
          <a
            className="media-heading fw-b"
            target="_self"
            href={`/deposit/project/${metadata._deposit.id}`}
          >
            {(metadata.title && metadata.title.title) || "No project title"}
          </a>
          {/* The browser closes the paragraph before the row, as before */}
          <p className="f8 mt-5 text-muted" />
          <div className="cds-row">
            <div className="cds-col-md-8">
              {videos.slice(0, 3).map((video, index) => (
                // eslint-disable-next-line react/no-array-index-key
                <div key={index} className="pl-20">
                  #{index + 1}:{" "}
                  {wordsSplit(
                    (video.title && video.title.title) || "No video title",
                    8
                  )}{" "}
                  {video.report_number && (
                    <span className="ui label cds-label cds-label-primary ml-10">
                      {" "}
                      {video.report_number[0]}{" "}
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div className="cds-col-md-4">
              {status !== "published" && (
                <ul className="list-unstyled">
                  {orderTasks(metadata._cds && metadata._cds.state).map(
                    ([task, taskStatus]) => (
                      <li className="small" key={task}>
                        <i
                          className={`fa fa-fw ${progressIcon(
                            taskStatus
                          )} ${progressClass(taskStatus)}`}
                        />{" "}
                        {taskRepr(task)}
                      </li>
                    )
                  )}
                </ul>
              )}
            </div>
          </div>
          <p />
          <ul className="cds-list-inline pull-left w-100 text-muted">
            <li className="f9">
              <small>
                <i className="fa fa-video-camera" /> {videos.length}
              </small>
            </li>{" "}
            <li className="f9">
              <small>
                <i className="fa fa-calendar" />{" "}
                {formatDate(record.created, "dd/MM/yyyy")}
              </small>
            </li>{" "}
            <li className="f9">
              {metadata.category && (
                <span className="ui label cds-label cds-label-sm cds-label-default">
                  {metadata.category}
                </span>
              )}{" "}
              {metadata.type && (
                <span className="ui label cds-label cds-label-sm cds-label-warning">
                  {metadata.type}
                </span>
              )}
            </li>
          </ul>
        </div>
        <div className="media-right media-object text-right">
          {status === "draft" && (
            <small>
              <i className="fa fa-edit" /> Draft
            </small>
          )}
          {status === "published" && (
            <small>
              <i className="fa fa-check text-primary" /> Published
            </small>
          )}
        </div>
      </li>
    </ul>
  );
}

DepositItem.propTypes = { record: PropTypes.object.isRequired };

function GetStarted({ text, wrapped }) {
  const content = (
    <div className="cds-jumbotron" style={{ textAlign: "center" }}>
      <h1>Get started!</h1>
      <p>{text}</p>
      {wrapped ? (
        <h1>
          <a className="ui large green button" href="/deposit/new">
            <i className="fa fa-upload" /> New Upload
          </a>
        </h1>
      ) : (
        <a className="ui large green button mt-20" href="/deposit/new">
          <i className="fa fa-upload" /> New Upload
        </a>
      )}
    </div>
  );
  if (!wrapped) {
    return content;
  }
  return (
    <div className="cds-list-group">
      <div className="cds-list-group-item">{content}</div>
    </div>
  );
}

GetStarted.propTypes = {
  text: PropTypes.string.isRequired,
  wrapped: PropTypes.bool.isRequired,
};

/** Results of the deposit list (``cds_deposit/search/results.html``). */
export function DepositResults() {
  const [state] = useSearch();
  const results = state.results;
  if (!results.hits) {
    return null;
  }
  const total = results.hits.total;
  const query = state.currentParams.q;
  const statusBuckets =
    ((results.aggregations || {}).status || {}).buckets || [];
  return (
    <>
      {total !== 0 && (
        <div>
          {(results.hits.hits || []).map((record) => (
            <DepositItem key={record.id} record={record} />
          ))}
        </div>
      )}
      {total === 0 && query && (
        <div className="cds-list-group">
          <div className="cds-list-group-item">
            <div>
              <div className="text-center mt-30 mb-30">
                <i className="fa fa-search f2" />
              </div>
              <p className="f5 text-center">
                no projects for found for <em>&quot;{query}&quot;</em>
              </p>
            </div>
          </div>
        </div>
      )}
      {total === 0 && !query && statusBuckets.length === 0 && (
        <div>
          <GetStarted text="Make your first upload." wrapped={false} />
        </div>
      )}
      {total === 0 && !query && statusBuckets.length !== 0 && (
        <div>
          <GetStarted text="Upload a new video." wrapped />
        </div>
      )}
    </>
  );
}

export const DEPOSIT_INDEX_COMPONENTS = {
  depositsearchbar: ({ data }) => (
    <DepositSearchBar placeholder={data.placeholder || ""} />
  ),
};

export const DEPOSIT_INDEX_TEMPLATES = {
  deposit: DepositResults,
};

/** Placeholder of the deposit list while it is loading. */
export function DepositResultsPlaceholder() {
  return (
    <div aria-busy="true">
      {[0, 1, 2, 3].map((index) => (
        <ul key={index} className="cds-deposit-media-list media-list">
          <li className="media mb-10 pa-5 cds-deposit-media-list-border">
            <div className="media-body">
              <Placeholder
                fluid
                className="cds-placeholder cds-placeholder-deposit"
              >
                <Placeholder.Header>
                  <Placeholder.Line length="medium" />
                </Placeholder.Header>
                <Placeholder.Paragraph>
                  <Placeholder.Line length="long" />
                  {index % 2 === 1 && <Placeholder.Line length="long" />}
                  <Placeholder.Line length="very short" />
                </Placeholder.Paragraph>
              </Placeholder>
            </div>
          </li>
        </ul>
      ))}
    </div>
  );
}

export const DEPOSIT_INDEX_PLACEHOLDERS = {
  deposit: DepositResultsPlaceholder,
};
