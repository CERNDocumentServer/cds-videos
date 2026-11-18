/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Chapters of a video, with their frames. */

import React, { useState } from "react";
import PropTypes from "prop-types";

import { chapterFrameUrl } from "@js/cds/shared/utils/images";

import { cleanHtmlFromTitle } from "./metadata";

export function ChaptersSection({
  chapters,
  chapterFrames,
  onViewAll,
  onJump,
}) {
  return (
    <div className="cds-detail-chapters px-20 mb-10">
      <hr />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "10px",
        }}
      >
        <h3>
          <strong>Chapters</strong>
        </h3>
        <button
          type="button"
          className="ui small basic button transcription-button"
          onClick={onViewAll}
        >
          View All
        </button>
      </div>
      <div
        className="chapters-main-horizontal"
        style={{ overflowX: "auto", overflowY: "hidden", whiteSpace: "nowrap" }}
      >
        <div
          style={{
            display: "inline-flex",
            gap: "15px",
            paddingBottom: "8px",
            paddingTop: "8px",
          }}
        >
          {chapters.map((chapter, index) => (
            <HorizontalChapter
              key={`${index}-${chapter.seconds}`}
              chapter={chapter}
              frame={chapterFrames[chapter.seconds]}
              onJump={onJump}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

ChaptersSection.propTypes = {
  chapters: PropTypes.array.isRequired,
  chapterFrames: PropTypes.object.isRequired,
  onViewAll: PropTypes.func.isRequired,
  onJump: PropTypes.func.isRequired,
};

function HorizontalChapter({ chapter, frame = null, onJump }) {
  const [hover, setHover] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <div
      className="chapter-item-horizontal-main"
      onClick={() => onJump(chapter.seconds)}
      onKeyDown={(e) => e.key === "Enter" && onJump(chapter.seconds)}
      onMouseOver={() => setHover(true)}
      onMouseOut={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      role="button"
      tabIndex={0}
      style={{
        display: "inline-block",
        cursor: "pointer",
        width: "213px",
        flexShrink: 0,
        padding: "12px",
        border: `1px solid ${hover ? "#2196F3" : "#e1e8ed"}`,
        borderRadius: "8px",
        transition: "all 0.2s ease",
        backgroundColor: hover ? "#f8f9fa" : "white",
        transform: hover ? "translateY(-2px)" : "translateY(0)",
      }}
    >
      <div
        className="chapter-thumbnail-main-horizontal"
        style={{
          width: "189px",
          height: "106px",
          borderRadius: "6px",
          overflow: "hidden",
          backgroundColor: "#f5f5f5",
          marginBottom: "8px",
          position: "relative",
        }}
      >
        {frame && !failed && (
          <img
            src={chapterFrameUrl(frame)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            alt={`Chapter ${chapter.timestamp}`}
            onError={() => setFailed(true)}
          />
        )}
        {!frame && (
          <div
            style={{
              width: "100%",
              height: "100%",
              backgroundColor: "#e9ecef",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <i
              className="fa fa-film"
              style={{ color: "#6c757d", fontSize: "20px" }}
            />
          </div>
        )}
        <div
          style={{
            position: "absolute",
            bottom: "4px",
            right: "4px",
            backgroundColor: "rgba(0,0,0,0.8)",
            color: "white",
            padding: "2px 4px",
            borderRadius: "2px",
            fontSize: "11px",
            fontWeight: 500,
          }}
        >
          {chapter.timestamp}
        </div>
      </div>
      <div className="chapter-info-main-horizontal">
        <div
          style={{
            fontSize: "13px",
            fontWeight: 600,
            lineHeight: 1.3,
            color: "#333",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "normal",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            lineClamp: 2,
            WebkitBoxOrient: "vertical",
            maxHeight: "2.6em",
          }}
        >
          {cleanHtmlFromTitle(chapter.title)}
        </div>
      </div>
    </div>
  );
}

HorizontalChapter.propTypes = {
  chapter: PropTypes.object.isRequired,
  frame: PropTypes.object,
  onJump: PropTypes.func.isRequired,
};
