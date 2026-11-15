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
 * Formik fields of the deposit forms, with the markup and the behaviour of
 * the former angular-schema-form decorators: label (``*`` when required),
 * widget, then the description or the validation message.
 *
 * Every change is also written to the deposit record (the actions send the
 * record), and marks the deposit dirty.
 */

import React, { useContext, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { getIn, useFormikContext } from "formik";
import _toPath from "lodash/toPath";
import DOMPurify from "dompurify";
import { useDispatch, useSelector, useStore } from "react-redux";
import { Placeholder } from "semantic-ui-react";

import { DialogModal } from "@js/cds/components/DialogModal";

import { parseAutocomplete } from "../filters";
import { removeBackendError, setRecordValue } from "../state/deposit";
import { isPublished } from "../state/records";
import { registerField } from "../state/registry";
import { AsyncMultiSelect, AsyncSelect } from "./AsyncSelect";
import {
  autocompleteAuthors,
  autocompleteKeywords,
  autocompleteLicenses,
  formatTokenTags,
} from "./autocomplete";
import { DatePickerInput } from "./DatePicker";

/** The deposit of the form: ``{id, type}``. */
export const DepositFormContext = React.createContext({ id: null, type: null });

export function useDepositForm() {
  return useContext(DepositFormContext);
}

/** Value, error and setter of a field. */
export function useDepositField(name, errorName) {
  const formik = useFormikContext();
  const dispatch = useDispatch();
  const { id } = useDepositForm();
  const errorPath = errorName || name;
  const value = getIn(formik.values, name);
  const touched = Boolean(getIn(formik.touched, name));
  const clientError = getIn(formik.errors, errorPath);
  const key = _toPath(name).join(".");
  // The server errors are shown on the field of the same key, as before
  const backendError = useSelector(
    (state) => state.deposits[id].backendErrors[key]
  );
  useEffect(() => registerField(id, key), [id, key]);
  const error =
    backendError ||
    (touched && typeof clientError === "string" ? clientError : null);
  const setValue = (newValue) => {
    formik.setFieldValue(name, newValue);
    formik.setFieldTouched(name, true, false);
    dispatch(setRecordValue(id, name, newValue));
  };
  return { value, error, setValue, formik, id, dispatch };
}

/** The deposit of the form is published. */
export function usePublished() {
  const { id } = useDepositForm();
  return useSelector((state) => isPublished(state.deposits[id].record));
}

/** Read only when the deposit is published (``formDefaults.readonly``). */
export function useReadonly(extra) {
  return usePublished() || Boolean(extra);
}

export function FormGroup({
  label = null,
  required = false,
  error = null,
  description = null,
  className = null,
  faIcon = null,
  notitle = false,
  nbsp = true,
  noHelp = false,
  children = null,
}) {
  return (
    <div
      className={["field cds-form-group", error && "has-error", className]
        .filter(Boolean)
        .join(" ")}
    >
      {!notitle && label && (
        <label
          className={["control-label", required && "field-required"]
            .filter(Boolean)
            .join(" ")}
        >
          {faIcon && <i className={`fa fa-fw ${faIcon}`} />}
          {nbsp && " "}
          {label}
        </label>
      )}
      {children}
      {!noHelp && <div className="help-block">{error || description}</div>}
    </div>
  );
}

FormGroup.propTypes = {
  label: PropTypes.node,
  required: PropTypes.bool,
  error: PropTypes.string,
  description: PropTypes.node,
  className: PropTypes.string,
  faIcon: PropTypes.string,
  notitle: PropTypes.bool,
  nbsp: PropTypes.bool,
  noHelp: PropTypes.bool,
  children: PropTypes.node,
};

/* Text input (``default.html``) */
export function TextField({
  name,
  label = null,
  placeholder = "",
  description = null,
  required = false,
  readonly = false,
  notitle = false,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly(readonly);
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      notitle={notitle}
    >
      <input
        type="text"
        name={_toPath(name).slice(-1)[0]}
        className="cds-form-control"
        placeholder={placeholder}
        value={value === undefined || value === null ? "" : value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      />
    </FormGroup>
  );
}

TextField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
  readonly: PropTypes.bool,
  notitle: PropTypes.bool,
};

/* Text area (``textarea.html``) */
export function TextAreaField({
  name,
  label = null,
  placeholder = "",
  description = null,
  required = false,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      nbsp={false}
    >
      <textarea
        className="cds-form-control"
        name={_toPath(name).slice(-1)[0]}
        placeholder={placeholder}
        value={value || ""}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      />
    </FormGroup>
  );
}

TextAreaField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
};

/* Select with fixed options (``select.html``) */
export function SelectField({
  name,
  label = null,
  options,
  description = null,
  required = false,
  readonly = false,
  onChange = null,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly(readonly);
  const known = options.some((option) => option.value === value);
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      description={description}
      nbsp={false}
    >
      <select
        className="cds-form-control"
        name={_toPath(name).slice(-1)[0]}
        value={known ? value : ""}
        disabled={disabled}
        onChange={(e) => {
          const option = options.find(
            (item) => String(item.value) === e.target.value
          );
          const newValue = option ? option.value : undefined;
          setValue(newValue);
          if (onChange) onChange(newValue);
        }}
      >
        {!known && <option value="" />}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.name}
          </option>
        ))}
      </select>
    </FormGroup>
  );
}

SelectField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  options: PropTypes.array.isRequired,
  description: PropTypes.node,
  required: PropTypes.bool,
  readonly: PropTypes.bool,
  onChange: PropTypes.func,
};

/* Checkbox (``checkbox.html``) */
export function CheckboxField({ name, label, description = null }) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  return (
    <div
      className={["cds-checkbox", error && "has-error"]
        .filter(Boolean)
        .join(" ")}
    >
      <label>
        <input
          type="checkbox"
          name={_toPath(name).slice(-1)[0]}
          checked={Boolean(value)}
          disabled={disabled}
          onChange={(e) => setValue(e.target.checked)}
        />{" "}
        <span>{label}</span>
      </label>
      <div className="help-block">{error || description}</div>
    </div>
  );
}

CheckboxField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  description: PropTypes.node,
};

/* Date (``datepicker.html``) */
export function DateField({
  name,
  label = null,
  placeholder = "",
  description = null,
  required = false,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  return (
    <FormGroup
      label={label}
      required={required}
      error={error}
      faIcon="fa-calendar"
      className="schema-form-datepicker"
      noHelp
    >
      <div>
        <DatePickerInput
          name={_toPath(name).slice(-1)[0]}
          placeholder={placeholder}
          value={value || ""}
          disabled={disabled}
          onChange={setValue}
        />
        <span className="help-block">{error || description}</span>
      </div>
    </FormGroup>
  );
}

DateField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
};

/* CKEditor 4 (``ckeditor.html``) */

const SANITIZE_CONFIG = {
  ALLOWED_TAGS: [
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "br",
    "code",
    "col",
    "colgroup",
    "div",
    "table",
    "tbody",
    "tfoot",
    "thead",
    "td",
    "th",
    "tr",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strike",
    "strong",
    "sub",
    "sup",
    "u",
    "ul",
  ],
  ALLOWED_ATTR: [
    "style",
    "dir",
    "lang",
    "color",
    "href",
    "title",
    "target",
    "rel",
  ],
  ALLOW_STYLE: true,
  ALLOW_DATA_ATTR: false,
};

/** Sanitize the HTML of the editor (``ckeditor-sanitizer.js``). */
export function sanitizeHtml(html) {
  if (!html || typeof html !== "string") {
    return html;
  }
  return DOMPurify.sanitize(html, SANITIZE_CONFIG);
}

/**
 * The content of an editor while CKEditor loads its plugins and skin: the
 * text is readable at once, in a box of the size of the editor.
 */
function CKEditorLoading({ html = "", height }) {
  return (
    <div className="cds-ckeditor-loading" aria-busy="true">
      <div className="cds-ckeditor-loading-toolbar">
        <Placeholder className="cds-placeholder">
          <Placeholder.Line length="full" />
        </Placeholder>
      </div>
      <div
        className="cds-ckeditor-loading-content"
        style={{ height }}
        dangerouslySetInnerHTML={{ __html: sanitizeHtml(html || "") }}
      />
      <div className="cds-ckeditor-loading-bottom" />
    </div>
  );
}

CKEditorLoading.propTypes = {
  html: PropTypes.string,
  height: PropTypes.number.isRequired,
};

// CKEditor 4 (about 620 KB) defines ``window.CKEDITOR`` and loads its plugins
// and skin from ``CKEDITOR_BASEPATH``: load it with the first editor, after
// the form is shown
let ckeditor;
function loadCKEditor() {
  ckeditor = ckeditor || import("ckeditor").then(() => window.CKEDITOR);
  return ckeditor;
}

export function CKEditorField({
  name,
  label = null,
  description = null,
  required = false,
  config,
}) {
  const { value, error, setValue } = useDepositField(name);
  const disabled = useReadonly();
  const [ready, setReady] = useState(false);
  const textarea = useRef(null);
  const editor = useRef(null);
  const settingData = useRef(false);
  const latest = useRef({ value, setValue, disabled });
  latest.current = { value, setValue, disabled };

  useEffect(() => {
    let active = true;
    let instance = null;
    loadCKEditor().then((CKEDITOR) => {
      if (!active || !CKEDITOR || !textarea.current) return;
      instance = CKEDITOR.replace(textarea.current, {
        // The default width of ng-ckeditor (the borders overflow the field)
        width: "100%",
        ...config,
        readOnly: latest.current.disabled,
      });
      editor.current = instance;
      const onChange = () => {
        if (settingData.current) return;
        const data = sanitizeHtml(instance.getData());
        if (data !== (latest.current.value || "")) {
          latest.current.setValue(data);
        }
      };
      instance.on("change", onChange);
      instance.on("instanceReady", () => {
        settingData.current = true;
        // An empty value is an empty paragraph, as with ng-ckeditor
        instance.setData(latest.current.value || "<p></p>", {
          callback: () => {
            settingData.current = false;
            setReady(true);
          },
        });
      });
    });
    return () => {
      active = false;
      if (instance) {
        try {
          instance.destroy(true);
        } catch (e) {
          // Already destroyed
        }
      }
      editor.current = null;
    };
    // The editor is created once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Values changed from outside (inherited or extracted metadata, saves)
  useEffect(() => {
    const instance = editor.current;
    if (!instance || instance.status !== "ready") return;
    const current = sanitizeHtml(instance.getData());
    if ((value || "") !== current) {
      settingData.current = true;
      instance.setData(value || "<p></p>", {
        callback: () => {
          settingData.current = false;
        },
      });
    }
  }, [value]);

  useEffect(() => {
    const instance = editor.current;
    if (instance && instance.status === "ready") {
      instance.setReadOnly(disabled);
    }
  }, [disabled]);

  return (
    <div
      className={["field cds-form-group", error && "has-error"]
        .filter(Boolean)
        .join(" ")}
    >
      {label && (
        <label
          className={["control-label", required && "field-required"]
            .filter(Boolean)
            .join(" ")}
        >
          {label}
        </label>
      )}
      {!ready && <CKEditorLoading html={value} height={config.height} />}
      <textarea
        ref={textarea}
        className="cds-form-control"
        style={{ backgroundColor: "white", display: "none" }}
        // The content is set when the editor is ready (one undo step, as before)
        defaultValue=""
        disabled={disabled}
      />
      <span className="help-block">{error || description}</span>
    </div>
  );
}

CKEditorField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
  config: PropTypes.object.isRequired,
};

/* Keywords (``uiselectmultiple.html`` with tagging) */
export function KeywordsField({
  name,
  label = null,
  placeholder = "",
  description = null,
}) {
  const { value, error, setValue, id } = useDepositField(name);
  const disabled = useReadonly();
  const store = useStore();
  // The keywords of the record when the form is created, as before
  const [fetch] = useState(() => {
    const { keywords } = store.getState().deposits[id].record;
    return (query) => autocompleteKeywords(keywords)(query);
  });
  return (
    <div
      className={["field cds-form-group", error && "has-error"]
        .filter(Boolean)
        .join(" ")}
    >
      <label className="control-label">{label}</label>
      <AsyncMultiSelect
        values={value || []}
        getName={(item) => item.name}
        toItem={formatTokenTags}
        fetchOptions={fetch}
        minLength={1}
        delay={100}
        disabled={disabled}
        placeholder={placeholder}
        allowAdditions
        onChange={setValue}
      />
      <div className="help-block">{error || description}</div>
    </div>
  );
}

KeywordsField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
};

/* Select with suggestions (``uiselect.html``) */
export function RemoteSelectField({
  name,
  errorName = null,
  label = null,
  placeholder = "",
  description = null,
  required = false,
  fetchOptions,
  minLength = 3,
  delay = 100,
  onSelect = null,
}) {
  const { value, error, setValue } = useDepositField(name, errorName);
  const disabled = useReadonly();
  return (
    <div
      className={[
        "field cds-form-group schema-form-uiselect",
        error && "has-error",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <label
        className={["control-label", required && "field-required"]
          .filter(Boolean)
          .join(" ")}
      >
        {" "}
        {label}
      </label>
      <AsyncSelect
        text={parseAutocomplete(value) || ""}
        // ui-select showed the placeholder only without a value (an empty
        // contributor ``{}`` is a value)
        placeholder={
          value === undefined || value === null || value === ""
            ? placeholder
            : ""
        }
        fetchOptions={fetchOptions}
        minLength={minLength}
        delay={delay}
        disabled={disabled}
        onSelect={(item) =>
          onSelect ? onSelect(item, setValue) : setValue(item.value)
        }
      />
      <div className="help-block">{error || description}</div>
    </div>
  );
}

RemoteSelectField.propTypes = {
  name: PropTypes.string.isRequired,
  errorName: PropTypes.string,
  label: PropTypes.string,
  placeholder: PropTypes.string,
  description: PropTypes.node,
  required: PropTypes.bool,
  fetchOptions: PropTypes.func.isRequired,
  minLength: PropTypes.number,
  delay: PropTypes.number,
  onSelect: PropTypes.func,
};

/* Arrays (``array.html``) */
export function ArrayField({
  name,
  label = null,
  required = false,
  add = null,
  description = null,
  inline = false,
  firstItemMessage = null,
  notitle = false,
  startEmpty = true,
  newItem = null,
  renderItem,
}) {
  const { value, error, setValue, formik, id, dispatch } =
    useDepositField(name);
  const disabled = useReadonly();
  const items = Array.isArray(value) ? value : [];

  // ``startEmpty: false``: an empty array gets a first item
  useEffect(() => {
    if (!startEmpty && items.length === 0) {
      const next = [{}];
      formik.setFieldValue(name, next, false);
      dispatch(setRecordValue(id, name, next));
    }
    // Only when the form is created
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const minLength = 1;
  return (
    <div
      className={["form-group schema-form-array clearfix", error && "has-error"]
        .filter(Boolean)
        .join(" ")}
    >
      {!notitle && label && (
        <label
          className={["control-label", required && "field-required"]
            .filter(Boolean)
            .join(" ")}
        >
          {" "}
          {label}
        </label>
      )}
      <ul className="list-unstyled">
        {items.map((item, index) => {
          const first = Boolean(firstItemMessage) && index === 0;
          return (
            // eslint-disable-next-line react/no-array-index-key
            <li
              key={index}
              className={[
                "cds-list-group-item",
                inline && "deposit-inline",
                first && "bg-warn",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {!first && (
                <div
                  className={[
                    "close-container pull-right",
                    !inline && "clear-form",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{ paddingBottom: "20px" }}
                >
                  {!(disabled || items.length <= minLength) && (
                    <button
                      className="cds-close"
                      type="button"
                      onClick={() => {
                        const next = items.filter((_item, i) => i !== index);
                        setValue(next);
                      }}
                    >
                      <span aria-hidden="true">&times;</span>
                    </button>
                  )}
                </div>
              )}
              {first && (
                <div className="pb-20">
                  <span className="ui label cds-label cds-label-default">
                    {firstItemMessage}
                  </span>
                </div>
              )}
              <div className="cds-clearfix" />
              {renderItem(`${name}.${index}`, index)}
            </li>
          );
        })}
      </ul>
      <div>
        {(error || description) && (
          <div className="help-block">{error || description}</div>
        )}
        {!disabled && (
          <a
            href="#add"
            className="add-button"
            onClick={(e) => {
              e.preventDefault();
              setValue(items.concat([newItem ? newItem() : {}]));
            }}
          >
            <i className="fa fa-plus" />
            &nbsp;{add || "Add"}
          </a>
        )}
      </div>
    </div>
  );
}

ArrayField.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string,
  required: PropTypes.bool,
  add: PropTypes.string,
  description: PropTypes.node,
  inline: PropTypes.bool,
  firstItemMessage: PropTypes.string,
  notitle: PropTypes.bool,
  startEmpty: PropTypes.bool,
  newItem: PropTypes.func,
  renderItem: PropTypes.func.isRequired,
};

/* Information about custom authors (``custom_authors_dialog.html``) */
export function CustomAuthorsInfo() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <a
        href="#info"
        onClick={(e) => {
          e.preventDefault();
          setOpen(true);
        }}
      >
        <i className="pull-right fa fa-info" />
      </a>
      <DialogModal
        open={open}
        onClose={() => setOpen(false)}
        title="Custom authors"
      >
        <p>
          Start by typing an author name and suggestions will become available
          to choose from.
        </p>
        <p>
          If you wish to enter a custom author please use this format:
          &quot;Lastname, Firstname&quot;
        </p>
      </DialogModal>
    </>
  );
}

/* Contributors */
export function ContributorsField({ roles }) {
  const { id } = useDepositForm();
  const dispatch = useDispatch();
  const [fetchAuthors] = useState(() =>
    autocompleteAuthors("/api/ldap/cern-users/")
  );
  return (
    <ArrayField
      name="contributors"
      label="Contributors"
      required
      add="Add another contributor"
      startEmpty={false}
      renderItem={(path) => (
        <>
          <CustomAuthorsInfo />
          <RemoteSelectField
            name={path}
            errorName={`${path}.name`}
            label="Name"
            placeholder="Author name"
            required
            fetchOptions={fetchAuthors}
            minLength={3}
            delay={500}
            onSelect={(item, setValue) => {
              // The whole contributor is replaced (as with ui-select)
              setValue(item.value);
              dispatch(removeBackendError(id, `${path}.name`));
            }}
          />
          <SelectField
            name={`${path}.role`}
            label="Role"
            options={roles}
            required
          />
        </>
      )}
    />
  );
}

ContributorsField.propTypes = { roles: PropTypes.array.isRequired };

/* Licences */
export function LicensesField() {
  return (
    <ArrayField
      name="license"
      notitle
      firstItemMessage="General license"
      add="Add licences"
      inline
      renderItem={(path, index) => (
        <>
          <RemoteSelectField
            name={`${path}.license`}
            label="Licence"
            placeholder="Search for a license name..."
            fetchOptions={autocompleteLicenses}
            minLength={1}
            delay={100}
          />
          {index !== 0 && (
            <TextField
              name={`${path}.material`}
              label="Material"
              placeholder="Material"
            />
          )}
          <TextField
            name={`${path}.credit`}
            label="Credit"
            placeholder="Credit"
          />
        </>
      )}
    />
  );
}

/* Fieldset (``fieldset.html``) */
export function Fieldset({ title, description = null, children = null }) {
  const [collapsed, setCollapsed] = useState(false);
  const disabled = useReadonly();
  return (
    <fieldset className="schema-form-fieldset" disabled={disabled}>
      <div className="cds-panel deposit-panel">
        <div className="cds-panel-heading">
          <a
            className="panel-toggle"
            href="#toggle"
            onClick={(e) => {
              e.preventDefault();
              setCollapsed(!collapsed);
            }}
          >
            {title}
            <span className="pull-right">
              <i
                className={`fa ${
                  collapsed ? "fa-chevron-right" : "fa-chevron-down"
                }`}
              />
            </span>
          </a>
        </div>
        <div
          className="cds-panel-body"
          style={{ display: collapsed ? "none" : undefined }}
        >
          {description && <p>{description}</p>}
          {children}
        </div>
      </div>
    </fieldset>
  );
}

Fieldset.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.node,
  children: PropTypes.node,
};
