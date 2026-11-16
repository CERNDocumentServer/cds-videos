/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* The deposit page: a project and its videos (``deposits.html``). */

import React, { useState } from "react";
import PropTypes from "prop-types";
import { Provider, useDispatch } from "react-redux";

import { DialogModal } from "@js/cds/components/DialogModal";
import { ToasterContainer } from "@js/cds/components/Toaster";

import {
  useConfig,
  useLoading,
  usePage,
  useProjectRecord,
  useStarted,
} from "../state/hooks";
import { addVideoFiles, initPage } from "../state/page";
import { startDeposit } from "../state/tasks";
import { DepositFormPlaceholder } from "./DepositFormPlaceholder";
import { DropZone } from "./DropZone";
import { ProjectPanel } from "./ProjectPanel";
import { VideoPanel } from "./VideoPanel";
import { TaskList } from "./common";

function Project({ id }) {
  useStarted(startDeposit, id);
  return <ProjectPanel id={id} />;
}

Project.propTypes = { id: PropTypes.string.isRequired };

function Video({ id, index, onTranscodeInfo }) {
  useStarted(startDeposit, id);
  return <VideoPanel id={id} index={index} onTranscodeInfo={onTranscodeInfo} />;
}

Video.propTypes = {
  id: PropTypes.string.isRequired,
  index: PropTypes.number.isRequired,
  onTranscodeInfo: PropTypes.func.isRequired,
};

function UploadBox({ title }) {
  const dispatch = useDispatch();
  const extensions = useConfig().videoExtensions;
  return (
    <DropZone
      multiple
      accept={extensions}
      pattern={extensions}
      onFiles={(files, invalid) => dispatch(addVideoFiles(files, invalid))}
    >
      <div className="cds-deposit-box-upload-wrapper text-center">
        <p className="cds-deposit-box-upload-icon">
          <i className="fa fa-4x fa-video-camera" aria-hidden="true" />
        </p>
        <div className="cds-deposit-box-upload-content">
          <div className="cds-deposit-box-upload-title">
            <h3>{title}</h3>
          </div>
          <p className="cds-deposit-box-upload-description">
            You can also <strong>Drag &amp; Drop</strong> video files here
          </p>
          <p className="text-muted mt-20">
            supported files <mark>{extensions}</mark>
          </p>
        </div>
      </div>
    </DropZone>
  );
}

UploadBox.propTypes = { title: PropTypes.string.isRequired };

function Intro() {
  const { videoExtensions } = useConfig();
  return (
    <div>
      <div className="cds-container-fluid py-20">
        <div className="cds-row">
          <div className="cds-col-md-offset-3 cds-col-md-6">
            <div className="cds-deposit-box cds-deposit-box-upload-intro">
              <div className="text-muted">
                <div className="text-muted">
                  <h5 className="text-muted">
                    <strong>Tips</strong>
                  </h5>
                  <ul>
                    <li>
                      If you are uploading a <mark>Zoom recording</mark>, please
                      make sure that you have enabled the option{" "}
                      <a
                        href="https://videoconference.web.cern.ch/t/can-i-record-a-zoom-meeting/126"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Optimize for 3rd party video editor
                      </a>
                      . If not, the transcoding process to create different
                      video subformats might take long.
                    </li>
                    <li>
                      Supported video formats are <mark>{videoExtensions}</mark>
                    </li>
                    <li>
                      For best results, we recommend uploading{" "}
                      <mark>landscape</mark> videos encoded with{" "}
                      <mark>H.264</mark> video codec and <mark>24</mark> FPS
                      (Frames Per Second)
                    </li>
                    <li>
                      Ultra High Definition 8K videos are <strong>NOT</strong>{" "}
                      supported
                    </li>
                  </ul>
                </div>
                <hr className="my-30" />
                <div className="text-muted" />
                <p className="text-center">
                  Do <strong>NOT</strong> close the browser window/tab or
                  <br />
                  your laptop until the video upload is completed.
                </p>
              </div>
              <hr className="my-30" />
              <UploadBox title="Click here to select videos to upload" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TranscodingHelp({ open, onClose }) {
  return (
    <DialogModal open={open} onClose={onClose} title="Video transcoding">
      <p className="text-left">
        The video transcoding step creates several different video formats
        (qualities) to enable adaptive streaming and optimize how the video is
        watched on multiple devices with different screen resolutions or
        Internet connection latencies. It is a heavy and lengthy process.
      </p>
      <p className="text-left">
        The transcoding software will create such video formats automatically in
        the background after your upload. You can publish your video at any
        time, even if transcoding <strong>is still running or failed</strong>,
        given that it might take long to complete. We are constantly monitoring
        the transcoding process and we will intervene when needed.
      </p>
      <p className="text-left">
        <strong>Our recommendation</strong> is to publish the video as soon as
        at least one video format is ready. You can follow the status of the
        transcoding process by clicking on the <strong>Files</strong> tab of
        each video and then on the <strong>Show</strong> text in the section{" "}
        <strong>Extracted subformats</strong>.
      </p>
      <br />
      <p className="text-left">
        Please notice that the transcoding platform at CERN is provided by the
        Webcast service and it is not managed by the CDS service.
      </p>
    </DialogModal>
  );
}

TranscodingHelp.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

function DepositPage() {
  useStarted(initPage);
  const page = usePage();
  const metadata = useProjectRecord();
  const loading = useLoading();
  const max = useConfig().maxNumberOfVideos;
  const [helpShown, setHelpShown] = useState(false);
  const videos = page.videoIds;
  const showHelp = () => setHelpShown(true);

  return (
    <>
      <ToasterContainer timeout={8000} />
      {page.status === "loading" && (
        // An existing project is loading
        <DepositFormPlaceholder />
      )}
      {page.status === "new" && <Intro />}
      {page.status === "ready" && (
        <div id={metadata._deposit.id}>
          {/* Top status bar */}
          <div className="cds-deposit-avc-overall-status mb-20">
            <div className="cds-container-fluid">
              <div className="cds-row">
                <div className="cds-col-md-9">
                  <ul className="cds-list-inline text-left">
                    <TaskList
                      state={metadata._cds && metadata._cds.state}
                      onTranscodeInfo={showHelp}
                    />
                  </ul>
                </div>
                <div className="cds-col-md-3 text-right text-primary">
                  <i
                    className="fa fa-spinner fa-spin fa-fw"
                    style={{
                      display: loading ? undefined : "none",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
          <TranscodingHelp
            open={helpShown}
            onClose={() => setHelpShown(false)}
          />
          <div className="cds-container-fluid">
            <div className="cds-row">
              <div className="cds-col-md-12">
                <Project id={metadata._deposit.id} />
                {videos.map((id, index) => (
                  <Video
                    key={id}
                    id={id}
                    index={index}
                    onTranscodeInfo={showHelp}
                  />
                ))}
                {metadata._deposit.status === "published" && (
                  <div
                    id="cds-deposit-main-uploader"
                    className="mt-40 cds-deposit-panel cds-deposit-box"
                  >
                    <p className="f5 text-center text-muted">
                      <strong>Everything is published.</strong>
                    </p>
                    <p className="f8 text-center text-muted">
                      Click <strong>Edit Project</strong> to add more videos
                    </p>
                  </div>
                )}
                {metadata._deposit.status !== "published" &&
                  videos.length < max && (
                    <div
                      id="cds-deposit-main-uploader"
                      className="mt-40 cds-deposit-panel cds-deposit-box"
                    >
                      <UploadBox title="Click here to select more videos to upload" />
                    </div>
                  )}
                {videos.length >= max && (
                  <div className="mt-20 cds-deposit-panel cds-panel">
                    <div className="cds-panel-heading text-muted px-20 py-10">
                      <span className="text-muted">
                        <i className="fa fa-square" /> Max number of videos
                      </span>
                    </div>
                    <div className="cds-panel-body text-center">
                      <p>
                        This project has reached the{" "}
                        <strong>maximum number</strong> of videos ({max}).
                        <br />
                        Please start a new upload and create a new project to
                        add more videos.
                      </p>
                    </div>
                  </div>
                )}
                {page.duplicateVideos.length > 0 && (
                  <div className="cds-alert cds-alert-danger">
                    <p>
                      Multiple deposits with the same filename are not allowed:
                    </p>
                    <ul>
                      {page.duplicateVideos.map((file) => (
                        <li key={file}>{file}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      {page.status === "denied" && (
        <div>
          <div className="cds-container">
            <div className="cds-row">
              <h1>Permission denied</h1>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** The deposit page with its store. */
export function Deposits({ store }) {
  return (
    <Provider store={store}>
      <DepositPage />
    </Provider>
  );
}

Deposits.propTypes = { store: PropTypes.object.isRequired };
