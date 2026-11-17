/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

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
