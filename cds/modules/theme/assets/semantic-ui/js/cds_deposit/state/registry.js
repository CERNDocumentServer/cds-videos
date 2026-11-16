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
 * What the deposits keep outside of the state: the fields rendered by the
 * forms, the files waiting to be uploaded, the extracted metadata in the
 * local storage. None of it is rendered.
 */

import { storage } from "@js/cds/api";

/* Rendered fields: only they show the validation errors of the server */

const fields = new Map();

/** A field of a deposit form is rendered (``key`` as ``a.0.b``). */
export function registerField(id, key) {
  if (!fields.has(id)) {
    fields.set(id, new Map());
  }
  const keys = fields.get(id);
  keys.set(key, (keys.get(key) || 0) + 1);
  return () => {
    const count = keys.get(key) - 1;
    if (count > 0) {
      keys.set(key, count);
    } else {
      keys.delete(key);
    }
  };
}

export function isFieldRendered(id, key) {
  return fields.has(id) && fields.get(id).has(key);
}

/* Upload queues: ``{key, file, headers, isAdditional}`` per deposit */

const queues = new Map();

export function uploadQueue(id) {
  if (!queues.has(id)) {
    queues.set(id, []);
  }
  return queues.get(id);
}

export function forgetDeposit(id) {
  queues.delete(id);
  fields.delete(id);
}

/* Local storage of a deposit (``angular-local-storage``, ``cdsDeposit``) */

const STORAGE_PREFIX = "cdsDeposit";

export const depositStorage = {
  get(id, key) {
    const info = storage.get(STORAGE_PREFIX, id);
    return info && typeof info === "object" ? info[key] : undefined;
  },
  set(id, key, value) {
    const info = storage.get(STORAGE_PREFIX, id);
    storage.set(STORAGE_PREFIX, id, {
      ...(info && typeof info === "object" ? info : {}),
      [key]: value,
    });
  },
  remove(id) {
    storage.remove(STORAGE_PREFIX, id);
  },
};
