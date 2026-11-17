/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import DOMPurify from "dompurify";

/** Trusted HTML of the record, sanitized. */
export function sanitize(html) {
  return DOMPurify.sanitize(html || "", { ADD_ATTR: ["target"] });
}
