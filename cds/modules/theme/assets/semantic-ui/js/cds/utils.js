/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/**
 * Helpers ported from the filters of the former AngularJS ``cds`` module.
 * They keep the exact same semantics, so that the React views render the
 * same values as the old templates.
 */

import _find from "lodash/find";
import _filter from "lodash/filter";
import _get from "lodash/get";
import _groupBy from "lodash/groupBy";
import _isArray from "lodash/isArray";
import _isEmpty from "lodash/isEmpty";
import _matchesProperty from "lodash/matchesProperty";
import _orderBy from "lodash/orderBy";
import _reject from "lodash/reject";
import _template from "lodash/template";

import { ISO_LANGUAGES } from "./isoLanguages";

/** Find record's file with given context_type. */
export function findContextType(record, contextType) {
  if (!_isEmpty(record)) {
    const files = record.metadata ? record.metadata._files : record._files;
    return _find(files, (file) => file.context_type === contextType);
  }
  return undefined;
}

/** Find master video file in record's files. */
export function findMaster(record) {
  return findContextType(record, "master");
}

/** Find master video's frames, without the chapter frames. */
export function findFrames(record) {
  if (!record) return [];
  const master = findMaster(record);
  if (!master || !master.frame) return [];
  return master.frame.filter((frame) => !_get(frame, "tags.is_chapter_frame"));
}

/** Find closest video resolution label for a file. */
export function findResolution(file) {
  const height = parseInt(file.tags.height, 10);
  const width = parseInt(file.tags.width, 10);

  let selectedResolution = height.toString().concat("p");

  const heightsToQualities = {
    240: "240p",
    360: "360p",
    480: "480p",
    720: "720p",
    1024: "1024p",
    1080: "TBD",
    2160: "4K",
    4320: "8K",
  };

  Object.keys(heightsToQualities).forEach((resolution) => {
    if (height >= resolution) {
      selectedResolution = heightsToQualities[resolution];
    }
  });

  if (selectedResolution === "TBD") {
    const widthToQualities = {
      1920: "1080p",
      2048: "2K",
    };
    selectedResolution = widthToQualities[1920];
    Object.keys(widthToQualities).forEach((resolution) => {
      if (width >= resolution) {
        selectedResolution = widthToQualities[resolution];
      }
    });
  }
  return selectedResolution;
}

/** Find the poster of a record, or the first frame of the master file. */
export function findPoster(record) {
  const poster = findContextType(record, "poster");
  if (poster) {
    return poster;
  }
  const masterFile = findMaster(record);
  return _find(masterFile["frame"], (frame) => frame.key === "frame-1.jpg");
}

/** Find the gif animation of a master video file. */
export function findGif(masterFile) {
  return _find(masterFile["frames-preview"], (gif) => gif.key === "frames.gif");
}

const iiifTemplate = _template(
  "/api/iiif/v2/<%=bucket%>:<%=version_id%>:<%=key%>/full/!<%=size%>/0/default.<%=ext%>"
);

export const NOT_FOUND_IMAGE = "/static/img/not_found.png";

/** IIIF thumbnail of a record (``iiif`` filter). */
export function iiif(record, showGif, size) {
  try {
    const masterFile = findMaster(record);
    const objectVersion = showGif ? findGif(masterFile) : findPoster(record);
    return iiifTemplate({
      bucket: objectVersion.bucket_id,
      key: objectVersion.key,
      version_id: objectVersion.version_id,
      size: size.join(","),
      ext: showGif ? "gif" : "png",
    });
  } catch (error) {
    return NOT_FOUND_IMAGE;
  }
}

/** IIIF thumbnail of a search hit (``cdsSearchResults`` directive). */
export function getImagePreview(record, showGif, size) {
  try {
    let file;
    if (showGif) {
      const masterFile = findContextType(record, "master");
      file = _find(
        masterFile["frames-preview"],
        (gif) => gif.key === "frames.gif"
      );
    } else {
      file = findPoster(record);
    }
    return iiifTemplate({
      bucket: file.bucket_id,
      key: file.key,
      version_id: file.version_id,
      size: size.join(","),
      ext: showGif ? "gif" : "png",
    });
  } catch (error) {
    return NOT_FOUND_IMAGE;
  }
}

export function ellipsis(text, length) {
  if (text.length > length) {
    return text.substr(0, length) + " [...]";
  }
  return text;
}

export function middleEllipsis(text, length) {
  if (!text || text.length <= length) return text;
  const dotIndex = text.lastIndexOf(".");
  if (dotIndex > 0) {
    const namePart = text.substring(0, dotIndex);
    const extensionPart = text.substring(dotIndex);
    return namePart.substr(0, length) + " [...]" + extensionPart;
  }
  return text.substr(0, length) + " [...]";
}

/** Group items by a (deep) field, keeping the insertion order of groups. */
export function groupBy(items, field, defaultGroup) {
  return _groupBy(items, (e) => _get(e, field) || defaultGroup);
}

/** Split files in ``download`` and ``additional`` groups. */
export function groupDownloadable(items) {
  return _groupBy(items, (e) =>
    _get(e, "tags.download") === "true" ? "download" : "additional"
  );
}

/** Sort video subformats descending by height. */
export function sortVideosDescending(videos) {
  return _orderBy(videos, (video) => parseInt(video.tags.height), ["desc"]);
}

/** Files with the given media types. */
export function getFilesByType(files, types) {
  if (!_isArray(files) || !_isArray(types) || !types.length || !files.length) {
    return files;
  }
  return files.filter((file) => types.indexOf(file.media_type) !== -1);
}

/** Files without the given media types. */
export function getAllFilesExcept(files, types) {
  if (!_isArray(files) || !_isArray(types) || !types.length || !files.length) {
    return files;
  }
  return files.filter((file) => types.indexOf(file.media_type) === -1);
}

export function findBy(data, key, value) {
  if (!_isEmpty(data)) {
    return _filter(data, _matchesProperty(key, value));
  }
  return undefined;
}

export function removeBy(data, key, value) {
  if (!_isEmpty(data)) {
    return _reject(data, _matchesProperty(key, value));
  }
  return undefined;
}

/** Transform an URL into an absolute URL. */
export function absoluteURL(url) {
  if (url.startsWith("https://") || url.startsWith("http://")) {
    return url;
  }
  return "http://" + url;
}

/** Truncate words. */
export function wordsSplit(input, words) {
  if (words === undefined) return input;
  if (words <= 0) return "";
  if (input) {
    const inputWords = input.split(/\s+/);
    if (inputWords.length > words) {
      input = inputWords.slice(0, words).join(" ") + " [...]";
    }
  }
  return input;
}

export function isPublic(record) {
  return (
    _get(record, "_access") === undefined ||
    _get(record, "_access.read") === undefined ||
    _get(record, "_access.read").length === 0
  );
}

/** Translate ISO languages to language names (i.e. en -> English). */
export function isoToLanguage(code) {
  return ISO_LANGUAGES[code] || code;
}

/** Translate collection keys to display labels. */
export function collectionLabel(key) {
  if (!key) return key;
  const strKey = String(key);
  return strKey.includes("::") ? strKey.split("::").pop() : strKey;
}

export function formatRelationResourceType(input) {
  if (!input) return "";
  let formatted = input.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
  formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
  return formatted;
}

/** Join array or return the String. */
export function joinArray(item) {
  if (_isArray(item)) {
    return item.join(", ");
  }
  return item;
}

export function replace(text, replaceText, replaceWith) {
  if (text) {
    return text.replace(replaceText, replaceWith);
  }
  return undefined;
}

/** Format urls for download. */
export function download(url) {
  if (!url) {
    return url;
  }
  const re = /([?&].*)=[^?&]+/;
  if (url.match(re)) {
    return url + "&download";
  }
  return url + "?download";
}

/** Share URLs (see https://github.com/bradvin/social-share-urls). */
export function assembleShareURL(record, platform) {
  if (!record) {
    return undefined;
  }
  const title = encodeURIComponent(record.metadata.title.title);
  const description = encodeURIComponent(record.metadata.description);
  const currentPageAddress = encodeURIComponent(window.location.href);
  const platformMapping = {
    facebook: "https://www.facebook.com/sharer.php?u=" + currentPageAddress,
    twitter:
      "https://twitter.com/intent/tweet?url=" +
      currentPageAddress +
      "&text=" +
      title +
      "&hashtags=cern",
    linkedin:
      "https://www.linkedin.com/shareArticle?mini=true&url=" +
      currentPageAddress +
      "&title=" +
      title +
      "&summary=" +
      description +
      "&source=" +
      currentPageAddress,
    reddit:
      "https://reddit.com/submit?url=" + currentPageAddress + "&title=" + title,
    email:
      "mailto:?subject=" +
      title +
      "&body=" +
      description +
      "%0a" +
      currentPageAddress,
  };
  return platformMapping[platform];
}

export function escapeDoubleQuotes(text) {
  return text ? text.replace(/"/g, '\\"') : text;
}

export function encodeURIComponentFilter(text) {
  return text ? encodeURIComponent(text) : text;
}

export function bytesToHumanReadable(size) {
  function round(num, precision) {
    return Math.round(num * Math.pow(10, precision)) / Math.pow(10, precision);
  }
  let limit = Math.pow(1024, 4);
  if (size > limit) {
    return round(size / limit, 1) + " TB";
  } else if (size > (limit /= 1024)) {
    return round(size / limit, 1) + " GB";
  } else if (size > (limit /= 1024)) {
    return round(size / limit, 1) + " MB";
  } else if (size > 1024) {
    return Math.round(size / 1024) + " KB";
  }
  return size + " B";
}

/** Iframe embed code of a video (``previewIframe`` filter). */
export function previewIframe(reportNumber, external) {
  let url = "/video/" + reportNumber;
  if (external) {
    url = window.location.origin + url;
  }
  return (
    '<iframe scrolling="no"  src="' +
    url +
    '" width="560" height="315" frameborder="0" allowfullscreen></iframe>'
  );
}

/** Source of the preview iframe of a record (``previewIframeSrc`` filter). */
export function previewIframeSrc(id, key, external) {
  let url = "/record/" + id + "/preview/" + key;
  const timestamp = new URLSearchParams(window.location.search).get("t");
  if (timestamp) {
    url += "?t=" + timestamp;
  }
  if (external) {
    url = window.location.origin + url;
  }
  return url;
}

export function toInt(text) {
  return text ? parseInt(text) : text;
}

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function pad(number) {
  return number < 10 ? "0" + number : String(number);
}

/**
 * Format a date like the AngularJS ``date`` filter does, for the formats
 * used by the CDS templates (``dd MMMM yyyy`` and ``dd/MM/yyyy``).
 */
export function formatDate(value, format) {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  let date;
  if (typeof value === "string") {
    const match = value.match(/^(\d{4})-?(\d\d)-?(\d\d)$/);
    if (match) {
      // AngularJS parses date only strings as local dates
      date = new Date(+match[1], +match[2] - 1, +match[3]);
    } else {
      date = new Date(value);
    }
  } else {
    date = new Date(value);
  }
  if (isNaN(date.getTime())) {
    return value;
  }
  return format
    .replace("yyyy", String(date.getFullYear()))
    .replace("MMMM", MONTHS[date.getMonth()])
    .replace("MM", pad(date.getMonth() + 1))
    .replace("dd", pad(date.getDate()));
}

/**
 * AngularJS ``filter`` filter with a string expression: keep the items that
 * have any (deep) property containing the expression, case insensitive.
 */
export function angularFilter(items, expression) {
  if (!expression) {
    return items || [];
  }
  const needle = String(expression).toLowerCase();
  function matches(value) {
    if (value === null || value === undefined) {
      return false;
    }
    if (typeof value === "object") {
      return Object.keys(value).some(
        (key) => key.charAt(0) !== "$" && matches(value[key])
      );
    }
    return String(value).toLowerCase().indexOf(needle) > -1;
  }
  return (items || []).filter(matches);
}

/** Return the value of a lodash path in an object, or a default. */
export const get = _get;

/**
 * AngularJS ``filter`` filter with an object expression, for example
 * ``filter:{context_type:'subtitle', content_type:'vtt'}``: every property of
 * the pattern must be contained (case insensitive) in the item property.
 */
export function angularFilterBy(items, pattern) {
  const keys = Object.keys(pattern || {});
  return (items || []).filter((item) =>
    keys.every((key) => {
      const expected = pattern[key];
      if (expected === undefined || expected === null || expected === "") {
        return true;
      }
      if (item === null || item === undefined) {
        return false;
      }
      const actual = item[key];
      if (actual === undefined || actual === null) {
        return false;
      }
      if (typeof actual === "object") {
        return angularFilter([actual], expected).length > 0;
      }
      return (
        String(actual).toLowerCase().indexOf(String(expected).toLowerCase()) >
        -1
      );
    })
  );
}

/** Subtitle files of a record usable as transcripts (``vtt`` subtitles). */
export function getVttSubtitles(record) {
  return angularFilterBy(_get(record, "metadata._files"), {
    context_type: "subtitle",
    content_type: "vtt",
  });
}

export const isEmpty = _isEmpty;
