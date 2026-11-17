/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import axios from "axios";

/** Read a cookie (from https://www.w3schools.com/js/js_cookies.asp). */
export function getCookie(cname) {
  const name = cname + "=";
  const decodedCookie = decodeURIComponent(document.cookie);
  const ca = decodedCookie.split(";");
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) === " ") {
      c = c.substring(1);
    }
    if (c.indexOf(name) === 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}

/*
 * Requests in flight, used by the loading bar.
 */
const listeners = new Set();
let pending = 0;

function notify() {
  listeners.forEach((listener) => listener(pending));
}

export function onPendingRequestsChange(listener) {
  listeners.add(listener);
  // The loading bar is mounted after the first requests of the page started
  if (pending > 0) {
    listener(pending);
  }
  return () => listeners.delete(listener);
}

/**
 * Add the CDS behaviour to an axios instance: CSRF token on the unsafe
 * requests and tracking of the pending requests for the loading bar.
 */
export function setupInterceptors(instance) {
  instance.interceptors.request.use((config) => {
    const method = (config.method || "get").toUpperCase();
    if (["POST", "PUT", "PATCH", "DELETE"].indexOf(method) > -1) {
      config.headers = config.headers || {};
      if (!config.headers["X-CSRFToken"]) {
        config.headers["X-CSRFToken"] = getCookie("csrftoken");
      }
    }
    if (!config.ignoreLoadingBar) {
      config.__tracked = true;
      pending += 1;
      notify();
    }
    return config;
  });
  instance.interceptors.response.use(
    (response) => {
      done(response.config);
      return response;
    },
    (error) => {
      done(error.config);
      return Promise.reject(error);
    }
  );
  return instance;
}

function done(config) {
  if (config && config.__tracked) {
    config.__tracked = false;
    pending = Math.max(0, pending - 1);
    notify();
  }
}

/**
 * Axios instance used by all the CDS React apps.
 *
 * - JSON by default, like the AngularJS ``$http`` service.
 * - Adds the ``X-CSRFToken`` header to unsafe requests (REST_CSRF_ENABLED).
 * - Reports the pending requests to the loading bar, unless the request
 *   config has ``ignoreLoadingBar: true``.
 */
export const http = setupInterceptors(
  axios.create({
    headers: {
      Accept: "application/json, text/plain, */*",
    },
  })
);

/**
 * ``localStorage`` helpers with the keys of the previous interface, so that
 * the values it stored are still found.
 */
export const storage = {
  key(prefix, key) {
    return (prefix ? prefix + "." : "") + key;
  },
  get(prefix, key) {
    try {
      const item = window.localStorage.getItem(this.key(prefix, key));
      if (!item || item === "null") {
        return null;
      }
      try {
        return JSON.parse(item);
      } catch (e) {
        return item;
      }
    } catch (error) {
      return null;
    }
  },
  set(prefix, key, value) {
    try {
      window.localStorage.setItem(
        this.key(prefix, key),
        value === undefined ? null : JSON.stringify(value)
      );
      return true;
    } catch (error) {
      return false;
    }
  },
  remove(prefix, key) {
    try {
      window.localStorage.removeItem(this.key(prefix, key));
    } catch (error) {
      // Nothing to do
    }
  },
};
