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
 * Text input with a calendar popup, like the former angular-strap
 * ``bs-datepicker`` (``yyyy-MM-dd`` strings, closes on selection).
 */

import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";

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
const SHORT_MONTHS = MONTHS.map((month) => month.slice(0, 3));
const WEEK_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function pad(number) {
  return String(number).padStart(2, "0");
}

export function formatDate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}`;
}

export function parseDate(value) {
  const match = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(value || "");
  if (!match) {
    return null;
  }
  const date = new Date(
    Number(match[1]),
    Number(match[2]) - 1,
    Number(match[3])
  );
  return Number.isNaN(date.getTime()) ? null : date;
}

function sameDay(a, b) {
  return (
    a &&
    b &&
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function chunk(items, size) {
  const rows = [];
  for (let i = 0; i < items.length; i += size) {
    rows.push(items.slice(i, i + size));
  }
  return rows;
}

function Calendar({ selected = null, onSelect }) {
  const [view, setView] = useState(0); // 0 days, 1 months, 2 years
  const [viewDate, setViewDate] = useState(() => selected || new Date());
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const today = new Date();

  let title;
  let rows;
  let columns;
  let step;
  if (view === 0) {
    title = `${MONTHS[month]} ${year}`;
    const first = new Date(year, month, 1);
    const start = new Date(year, month, 1 - first.getDay());
    const days = [];
    for (let i = 0; i < 42; i += 1) {
      days.push(
        new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
      );
    }
    columns = 7;
    rows = chunk(
      days.map((day) => ({
        key: formatDate(day),
        label: pad(day.getDate()),
        muted: day.getMonth() !== month,
        active: sameDay(day, selected),
        today: sameDay(day, today),
        select: () => onSelect(day),
      })),
      7
    );
    step = (direction) => setViewDate(new Date(year, month + direction, 1));
  } else if (view === 1) {
    title = String(year);
    columns = 4;
    rows = chunk(
      SHORT_MONTHS.map((label, index) => ({
        key: label,
        label,
        active:
          selected &&
          selected.getFullYear() === year &&
          selected.getMonth() === index,
        select: () => {
          setViewDate(new Date(year, index, 1));
          setView(0);
        },
      })),
      4
    );
    step = (direction) => setViewDate(new Date(year + direction, month, 1));
  } else {
    const firstYear = year - (year % 12);
    title = `${firstYear}-${firstYear + 11}`;
    columns = 4;
    rows = chunk(
      Array.from({ length: 12 }, (_value, index) => firstYear + index).map(
        (value) => ({
          key: value,
          label: String(value),
          active: selected && selected.getFullYear() === value,
          select: () => {
            setViewDate(new Date(value, month, 1));
            setView(1);
          },
        })
      ),
      4
    );
    step = (direction) =>
      setViewDate(new Date(year + 12 * direction, month, 1));
  }

  return (
    <table className="cds-datepicker-table">
      <thead>
        <tr className="text-center">
          <th>
            <button
              tabIndex="-1"
              type="button"
              className="cds-datepicker-btn pull-left"
              onClick={() => step(-1)}
            >
              <i className="fa fa-chevron-left" />
            </button>
          </th>
          <th colSpan={columns - 2}>
            <button
              tabIndex="-1"
              type="button"
              className="cds-datepicker-btn cds-datepicker-title"
              onClick={() => setView(Math.min(view + 1, 2))}
            >
              <strong>{title}</strong>
            </button>
          </th>
          <th>
            <button
              tabIndex="-1"
              type="button"
              className="cds-datepicker-btn pull-right"
              onClick={() => step(1)}
            >
              <i className="fa fa-chevron-right" />
            </button>
          </th>
        </tr>
        {view === 0 && (
          <tr>
            {WEEK_DAYS.map((day) => (
              <th key={day} className="dow text-center">
                <small>{day}</small>
              </th>
            ))}
          </tr>
        )}
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row[0].key}>
            {row.map((cell) => (
              <td className="text-center" key={cell.key}>
                <button
                  tabIndex="-1"
                  type="button"
                  className={[
                    "cds-datepicker-btn",
                    cell.active && "active",
                    cell.today && "today",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={cell.select}
                >
                  <span className={cell.muted ? "text-muted" : undefined}>
                    {cell.label}
                  </span>
                </button>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

Calendar.propTypes = {
  selected: PropTypes.instanceOf(Date),
  onSelect: PropTypes.func.isRequired,
};

export function DatePickerInput({
  name = undefined,
  value = "",
  placeholder = "",
  disabled = false,
  onChange,
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const onDocument = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocument);
    return () => document.removeEventListener("mousedown", onDocument);
  }, [open]);

  return (
    <div className="cds-datepicker-wrapper" ref={ref}>
      <input
        type="text"
        className="cds-form-control"
        name={name}
        placeholder={placeholder}
        value={value || ""}
        disabled={disabled}
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape" || e.key === "Tab") {
            setOpen(false);
          }
        }}
        onChange={(e) => onChange(e.target.value)}
      />
      {open && !disabled && (
        // Keep the focus in the input when clicking the calendar
        // eslint-disable-next-line jsx-a11y/no-static-element-interactions
        <div
          className="cds-datepicker-dropdown"
          onMouseDown={(e) => e.preventDefault()}
        >
          <Calendar
            key={value}
            selected={parseDate(value)}
            onSelect={(date) => {
              onChange(formatDate(date));
              setOpen(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

DatePickerInput.propTypes = {
  name: PropTypes.string,
  value: PropTypes.string,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  onChange: PropTypes.func.isRequired,
};
