/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

/*
 * Toast notifications (replaces angularjs-toaster).
 *
 * Usage: ``toaster.pop({type, title, body})`` or
 * ``toaster.pop(type, title, body)``. ``body`` may contain trusted HTML.
 */
const subscribers = new Set();
let counter = 0;

export const toaster = {
  pop(typeOrOptions, title, body) {
    const toast =
      typeof typeOrOptions === "object"
        ? { ...typeOrOptions }
        : { type: typeOrOptions, title, body };
    toast.id = ++counter;
    subscribers.forEach((subscriber) => subscriber(toast));
    return toast.id;
  },
};

const TYPE_CLASSES = {
  error: "toast-error",
  info: "toast-info",
  wait: "toast-wait",
  success: "toast-success",
  warning: "toast-warning",
};

function Toast({ toast, onDismiss, timeout }) {
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused) {
      return undefined;
    }
    const timer = setTimeout(() => onDismiss(toast.id), timeout);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss, timeout, paused]);

  return (
    // The toasts are dismissed when clicked, as before
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div
      className={`toast ${TYPE_CLASSES[toast.type] || "toast-info"}`}
      onClick={() => onDismiss(toast.id)}
      onMouseOver={() => setPaused(true)}
      onFocus={() => setPaused(true)}
      onMouseOut={() => setPaused(false)}
      onBlur={() => setPaused(false)}
    >
      <div className="toast-title">{toast.title}</div>
      <div className="toast-message">
        <div>{toast.body}</div>
      </div>
    </div>
  );
}

Toast.propTypes = {
  toast: PropTypes.object.isRequired,
  onDismiss: PropTypes.func.isRequired,
  timeout: PropTypes.number.isRequired,
};

/** Container rendering the toasts (``<toaster-container>``), newest on top. */
export function ToasterContainer({ timeout }) {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const subscriber = (toast) => setToasts((current) => [toast, ...current]);
    subscribers.add(subscriber);
    return () => subscribers.delete(subscriber);
  }, []);

  const dismiss = React.useCallback(
    (id) => setToasts((current) => current.filter((t) => t.id !== id)),
    []
  );

  return (
    <div id="toast-container" className="toast-top-right">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          toast={toast}
          onDismiss={dismiss}
          timeout={timeout}
        />
      ))}
    </div>
  );
}

ToasterContainer.propTypes = {
  timeout: PropTypes.number,
};

ToasterContainer.defaultProps = {
  timeout: 5000,
};
