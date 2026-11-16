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
 * Helpers of the record page (functions of the former ``cdsRecordCtrl``).
 */

import { WebVTT } from "vtt.js";

import { findMaster } from "@js/cds/utils";

/** Convert seconds to ``m:ss``. */
export function convertToMinutesSeconds(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const paddedSecs = secs < 10 ? "0" + secs : secs;
  return `${minutes}:${paddedSecs}`;
}

/** Parse ``ss``, ``mm:ss`` or ``hh:mm:ss``. */
export function parseHMS(value) {
  if (value === null || value === undefined) return NaN;
  const txt = String(value).trim();
  if (!txt) return NaN;
  if (!/^\d{1,2}(?::\d{1,2}){0,2}$/.test(txt)) return NaN;
  const parts = txt.split(":").map(Number);
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] * 3600 + parts[1] * 60 + parts[2];
}

/** Remove the HTML tags of a chapter title. */
export function cleanHtmlFromTitle(title) {
  if (!title) return title;
  let cleanTitle = title.replace(/<[^>]+>/g, " ");
  cleanTitle = cleanTitle.replace(/\s+/g, " ").trim();
  return cleanTitle;
}

/**
 * Turn the timestamps of a description (``0:00``, ``00:00:00``...) into
 * links seeking the player. The clicks are handled by the description
 * container (``data-seconds``).
 */
export function processDescriptionWithClickableTimestamps(description) {
  if (!description) return description;
  const pattern = /(\d{1,2}:(?:\d{1,2}:)?\d{1,2})/g;
  return description.replace(pattern, (match) => {
    const timeParts = match.split(":");
    let totalSeconds;
    if (timeParts.length === 2) {
      const [minutes, seconds] = timeParts.map(Number);
      totalSeconds = minutes * 60 + seconds;
    } else if (timeParts.length === 3) {
      const [hours, minutes, seconds] = timeParts.map(Number);
      totalSeconds = hours * 3600 + minutes * 60 + seconds;
    } else {
      return match;
    }
    return `<a href="javascript:void(0)" class="timestamp-link" data-seconds="${totalSeconds}" style="color: #2196F3; font-weight: 600; cursor: pointer;">${match}</a>`;
  });
}

/** Short (first lines) and full descriptions with clickable timestamps. */
export function prepareDescriptions(description, previewLines) {
  if (!description) {
    return {
      shortDescription: "No description",
      fullDescription: "No description",
    };
  }
  const lines = description.split(/\r?\n/);
  const firstLines = lines.slice(0, previewLines).join("\n");
  return {
    shortDescription: processDescriptionWithClickableTimestamps(firstLines),
    fullDescription: processDescriptionWithClickableTimestamps(description),
  };
}

/** Related identifiers grouped by relation type (without Indico ones). */
export function prepareRelatedIdentifiers(metadata) {
  const grouped = {};
  (metadata.related_identifiers || []).forEach((original) => {
    if (original.scheme === "Indico") return;
    const item = { ...original };
    switch (item.scheme) {
      case "URL":
        item.url = item.identifier;
        break;
      case "CDS":
        item.url = `https://cds.cern.ch/record/${item.identifier}`;
        break;
      case "DOI":
        item.url = `https://doi.org/${item.identifier}`;
        break;
      default:
        return;
    }
    if (!grouped[item.relation_type]) {
      grouped[item.relation_type] = [];
    }
    grouped[item.relation_type].push(item);
  });
  return grouped;
}

/** Frame of each chapter: ``chapter-<seconds>.jpg`` or the closest frame. */
export function buildChapterFrames(record, chapters) {
  if (!record || !chapters) return {};
  const master = findMaster(record);
  if (!master || !master.frame) return {};
  const frames = master.frame;
  const matches = {};
  chapters.forEach((chapter) => {
    const expectedName = `chapter-${chapter.seconds}.jpg`;
    const frame = frames.find((f) => f.key === expectedName);
    if (frame) {
      matches[chapter.seconds] = frame;
    }
  });
  const missing = chapters.filter(
    (c) => !Object.prototype.hasOwnProperty.call(matches, c.seconds)
  );
  missing.forEach((chapter) => {
    const target = Number(chapter.seconds);
    let closest = null;
    let minDiff = Infinity;
    frames.forEach((frame) => {
      if (
        !frame.tags ||
        frame.tags.timestamp === null ||
        frame.tags.timestamp === undefined
      ) {
        return;
      }
      const diff = Math.abs(Number(frame.tags.timestamp) - target);
      if (diff < minDiff) {
        minDiff = diff;
        closest = frame;
      }
    });
    matches[chapter.seconds] = closest || null;
  });
  return matches;
}

/** Fetch and parse a VTT file: cues keyed by their text. */
export function parseVttFromUrl(url) {
  return fetch(url)
    .then((res) => res.text())
    .then((vttText) => {
      const parser = new WebVTT.Parser(window, WebVTT.StringDecoder());
      const cues = {};
      parser.oncue = (cue) => {
        cues[cue.text] = {
          start: cue.startTime,
          end: cue.endTime,
          text: cue.text,
        };
      };
      parser.parse(vttText);
      parser.flush();
      return cues;
    });
}

/** Lines of a transcript containing the search term. */
export function filterTranscript(transcript, search) {
  const searchTerm = (search || "").toLowerCase();
  return Object.values(transcript || {}).filter(
    (line) =>
      !searchTerm ||
      (line.text && line.text.toLowerCase().indexOf(searchTerm) !== -1)
  );
}

/** The player of the preview iframe, when exposed (THEOplayer). */
export function getPlayer() {
  try {
    return window.top.player;
  } catch (error) {
    return undefined;
  }
}

/** Seek the player and play. */
export function seekTo(timecode) {
  const player = getPlayer();
  if (player) {
    if (timecode < 0 || timecode > player.duration) {
      console.warn("Invalid timecode:", timecode);
      return;
    }
    player.currentTime = timecode;
    if (player.paused) {
      try {
        const playPromise = player.play();
        if (playPromise && playPromise.catch) {
          playPromise.catch((err) => {
            console.warn("Autoplay might be blocked by the browser:", err);
          });
        }
      } catch (err) {
        console.warn("Error playing video:", err);
      }
    }
  } else {
    console.warn("Player not available");
  }
}

/** Scroll to an element when it is not visible (below the navbar). */
export function scrollToElement(id) {
  setTimeout(() => {
    const el = document.getElementById(id);
    if (el) {
      const rect = el.getBoundingClientRect();
      const isVisible =
        rect.top >= 0 &&
        rect.bottom <=
          (window.innerHeight || document.documentElement.clientHeight);
      if (!isVisible) {
        const topOffset = rect.top + window.scrollY - 60;
        window.scrollTo({ top: topOffset, behavior: "smooth" });
      }
    } else {
      console.warn("Element not found:", id);
    }
  }, 100);
}

function getScrollableParent(element) {
  let el = element;
  while (el && el !== document.body) {
    const style = window.getComputedStyle(el);
    if (style.overflowY === "auto" || style.overflowY === "scroll") {
      return el;
    }
    el = el.parentElement;
  }
  return null;
}

/** Scroll the list containing the active item (``selector``) to it. */
export function scrollActiveIntoList(selector) {
  setTimeout(() => {
    const el = document.querySelector(selector);
    const container = getScrollableParent(el);
    if (el && container) {
      const elRect = el.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const targetScroll =
        container.scrollTop + (elRect.top - containerRect.top) - 10;
      container.scrollTo({ top: targetScroll, behavior: "smooth" });
    }
  }, 50);
}
