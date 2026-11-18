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
 * "In this video" panel next to the player: chapters and transcripts, which
 * follow the playback.
 */

import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";

import { chapterFrameUrl } from "@js/cds/shared/utils/images";
import { isoToLanguage } from "@js/cds/shared/utils/languages";

import {
  convertToMinutesSeconds,
  getPlayer,
  scrollActiveIntoList,
  seekTo,
} from "./playback";
import { cleanHtmlFromTitle } from "./metadata";

/**
 * Active transcript line and chapter, updated every 100ms from the player
 * position (and scrolled into view when they change).
 */
export function usePlayerHighlights(transcript, chapters) {
  const [currentTranscriptLine, setCurrentTranscriptLine] = useState(null);
  const [currentChapter, setCurrentChapter] = useState(null);
  const current = useRef({ line: null, chapter: null });
  const data = useRef({ transcript, chapters });
  data.current = { transcript, chapters };

  useEffect(() => {
    function updateTranscriptHighlight() {
      const player = getPlayer();
      if (!player || !data.current.transcript) return;
      const currentTime = player.currentTime;
      const lines = Object.values(data.current.transcript);
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (currentTime >= line.start && currentTime <= line.end) {
          if (current.current.line !== line) {
            current.current.line = line;
            setCurrentTranscriptLine(line);
            scrollActiveIntoList(".transcript-line.active");
          }
          return;
        }
      }
      current.current.line = null;
      setCurrentTranscriptLine(null);
    }

    function updateChapterHighlight() {
      const player = getPlayer();
      const list = data.current.chapters;
      if (!player || !list || list.length === 0) return;
      const currentTime = player.currentTime;
      for (let i = 0; i < list.length; i++) {
        const chapter = list[i];
        const nextChapter = list[i + 1];
        if (
          currentTime >= chapter.seconds &&
          (!nextChapter || currentTime < nextChapter.seconds)
        ) {
          if (current.current.chapter !== chapter) {
            current.current.chapter = chapter;
            setCurrentChapter(chapter);
            scrollActiveIntoList(".chapter-item.active");
          }
          return;
        }
      }
      current.current.chapter = null;
      setCurrentChapter(null);
    }

    const transcriptTimer = setInterval(updateTranscriptHighlight, 100);
    const chapterTimer = setInterval(updateChapterHighlight, 100);
    return () => {
      clearInterval(transcriptTimer);
      clearInterval(chapterTimer);
    };
  }, []);

  return { currentTranscriptLine, currentChapter };
}

function ChapterThumbnail({ chapter, frame = null }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="chapter-thumbnail">
      <div className={`thumbnail-container${frame ? "" : " is-placeholder"}`}>
        {frame && !failed && (
          // The same image as the chapters under the player. Lazy, as the
          // panel stays in the page hidden until it is opened
          <img
            src={chapterFrameUrl(frame)}
            loading="lazy"
            alt={`Chapter ${chapter.timestamp}`}
            onError={() => setFailed(true)}
          />
        )}
        <div
          className="thumbnail-placeholder"
          style={{ display: frame && !failed ? "none" : "flex" }}
        >
          <i className="fa fa-film" />
        </div>
      </div>
    </div>
  );
}

ChapterThumbnail.propTypes = {
  chapter: PropTypes.object.isRequired,
  frame: PropTypes.object,
};

export function InThisVideo({
  visible,
  activeTab,
  onActiveTab,
  onClose,
  chapters,
  chapterFrames,
  hasTranscripts,
  transcriptsByLanguage,
  selectedTranscriptLanguage = null,
  onTranscriptLanguage,
  transcriptSearch,
  onTranscriptSearch,
  filteredTranscript,
  currentTranscriptLine = null,
  currentChapter = null,
}) {
  return (
    <div
      className="cds-col-md-4 bg-b pt-20"
      id="inThisVideoSection"
      style={{ display: visible ? undefined : "none" }}
    >
      <div className="in-this-video-panel bg-w pl-10 pb-10 pr-10 pt-10">
        <div className="cds-detail-title cds-detail-video-title in-this-video-header">
          <h3 className="cds-title-section-decoration bt bw-1 pt-10 mb-0">
            <i className="fa fa-video-camera" /> In this video
          </h3>
          <h4>
            <i
              className="fa fa-close transcription-close"
              onClick={onClose}
              onKeyDown={(e) => e.key === "Enter" && onClose()}
              role="button"
              tabIndex={0}
              aria-label="Close"
            />
          </h4>
        </div>
        {/* Tabs */}
        <div className="tabs-container">
          <div className="ui tabular menu cds-nav-tabs">
            {chapters.length > 0 && (
              <a
                href="#chapters"
                className={`item${activeTab === "chapters" ? " active" : ""}`}
                onClick={(e) => {
                  e.preventDefault();
                  onActiveTab("chapters");
                }}
              >
                <i className="fa fa-list-ol" />
                &nbsp;Chapters
              </a>
            )}
            {hasTranscripts && (
              <a
                href="#transcript"
                className={`item${activeTab === "transcript" ? " active" : ""}`}
                onClick={(e) => {
                  e.preventDefault();
                  onActiveTab("transcript");
                }}
              >
                <i className="fa fa-align-left" />
                &nbsp;Transcript
              </a>
            )}
          </div>
        </div>
        {/* Transcript Tab */}
        <div
          className="transcript-content"
          style={{
            display:
              activeTab === "transcript" && hasTranscripts ? undefined : "none",
          }}
        >
          <div className="search-container">
            <div className="ui fluid input">
              <input
                type="text"
                placeholder="Search transcript..."
                value={transcriptSearch}
                onChange={(e) => onTranscriptSearch(e.target.value)}
              />
            </div>
          </div>
          <div
            className="content-container"
            style={{
              display: filteredTranscript.length > 0 ? undefined : "none",
            }}
          >
            <ul className="list-unstyled mb-0">
              {filteredTranscript.map((line, index) => (
                // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
                <li
                  key={`${index}-${line.start}`}
                  onClick={() => seekTo(line.start)}
                  className={`transcript-line transcript-item${
                    currentTranscriptLine === line ? " active" : ""
                  }`}
                >
                  <div className="transcript-timestamp">
                    {convertToMinutesSeconds(line.start)} -{" "}
                    {convertToMinutesSeconds(line.end)}
                  </div>
                  <div className="transcript-text">{line.text}</div>
                </li>
              ))}
            </ul>
          </div>
          <div className="field language-selector">
            <label htmlFor="cds-transcript-language">
              Transcript Language:
            </label>
            <select
              id="cds-transcript-language"
              className="ui fluid dropdown"
              value={selectedTranscriptLanguage || ""}
              onChange={(e) => onTranscriptLanguage(e.target.value)}
            >
              {!selectedTranscriptLanguage && <option value="" />}
              {Object.keys(transcriptsByLanguage).map((lang) => (
                <option key={lang} value={lang}>
                  {isoToLanguage(lang)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {/* Chapters Tab */}
        <div
          className="content-container"
          style={{
            display:
              activeTab === "chapters" && chapters.length > 0
                ? undefined
                : "none",
          }}
        >
          <ul className="list-unstyled mb-0">
            {chapters.map((chapter, index) => (
              // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
              <li
                key={`${index}-${chapter.seconds}`}
                onClick={() => seekTo(chapter.seconds)}
                className={`chapter-item${
                  currentChapter === chapter ? " active" : ""
                }`}
              >
                <div className="chapter-content">
                  <ChapterThumbnail
                    chapter={chapter}
                    frame={chapterFrames[chapter.seconds]}
                  />
                  <div className="chapter-info">
                    <div className="chapter-title">
                      {cleanHtmlFromTitle(chapter.title)}
                    </div>
                    <div className="chapter-timestamp">{chapter.timestamp}</div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

InThisVideo.propTypes = {
  visible: PropTypes.bool.isRequired,
  activeTab: PropTypes.string.isRequired,
  onActiveTab: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  chapters: PropTypes.array.isRequired,
  chapterFrames: PropTypes.object.isRequired,
  hasTranscripts: PropTypes.bool.isRequired,
  transcriptsByLanguage: PropTypes.object.isRequired,
  selectedTranscriptLanguage: PropTypes.string,
  onTranscriptLanguage: PropTypes.func.isRequired,
  transcriptSearch: PropTypes.string.isRequired,
  onTranscriptSearch: PropTypes.func.isRequired,
  filteredTranscript: PropTypes.array.isRequired,
  currentTranscriptLine: PropTypes.object,
  currentChapter: PropTypes.object,
};
