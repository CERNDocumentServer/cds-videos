/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Format text for display. */

import _isArray from "lodash/isArray";

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

export function escapeDoubleQuotes(text) {
  return text ? text.replace(/"/g, '\\"') : text;
}

export function bytesToHumanReadable(size) {
  const round = (num) => Math.round(num * 10) / 10;
  const [KB, MB, GB, TB] = [1024, 1024 ** 2, 1024 ** 3, 1024 ** 4];
  if (size > TB) {
    return round(size / TB) + " TB";
  } else if (size > GB) {
    return round(size / GB) + " GB";
  } else if (size > MB) {
    return round(size / MB) + " MB";
  } else if (size > KB) {
    return Math.round(size / KB) + " KB";
  }
  return size + " B";
}
