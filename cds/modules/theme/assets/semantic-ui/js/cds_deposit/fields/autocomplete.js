/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Remote suggestions of the deposit forms (from the former ``cdsForm``). */

import _capitalize from "lodash/capitalize";
import _findIndex from "lodash/findIndex";

import { http } from "@js/cds/api";

function stripCommas(string) {
  return string.replace(/,/g, "");
}

/** Prepend the user input as a custom value, unless it is already there. */
function prependUserInput(userInput, suggestions) {
  try {
    if (
      userInput &&
      _findIndex(
        suggestions,
        (suggestion) =>
          suggestion.name.toUpperCase() === userInput.name.toUpperCase()
      ) === -1
    ) {
      suggestions.unshift(userInput);
    }
  } catch (e) {
    // Nothing to do
  }
}

function autocomplete(url, paramsProvider, responseHandler, resultSize = 10) {
  return (query) => {
    if (!query) {
      return Promise.resolve([]);
    }
    return http
      .get(url, { params: paramsProvider(query), ignoreLoadingBar: false })
      .then((response) =>
        responseHandler(response, query).slice(0, resultSize)
      );
  };
}

/** Licences: ``{name, value}`` with the licence id. */
export const autocompleteLicenses = autocomplete(
  "/api/licenses/_suggest",
  (query) => ({ text: query }),
  (response) =>
    response.data.text[0].options.map((license) => {
      const value = license._source.id;
      return { name: value, value };
    })
);

function selectMultiple(name, keyId) {
  const value = { name };
  if (keyId) {
    value.key_id = keyId;
  }
  return { name, value };
}

/** Keywords: ``{name, value: {name, key_id}}``, the record keywords too. */
export function autocompleteKeywords(currentKeywords) {
  return autocomplete(
    "/api/keywords/_suggest",
    (query) => ({ "suggest-name": query }),
    (response, query) => {
      const userInput = selectMultiple(query);
      const suggestions = response.data["suggest-name"][0].options
        .concat(currentKeywords || [])
        .map((keyword) =>
          selectMultiple(
            keyword._source ? keyword._source.name : keyword.name,
            keyword._source ? keyword._source.key_id : null
          )
        );
      prependUserInput(userInput, suggestions);
      return suggestions;
    }
  );
}

/** Keyword typed by the user (``formatTokenTags``). */
export function formatTokenTags(item) {
  return { name: item, value: { name: item } };
}

function formAuthor(author) {
  return {
    text: stripCommas(author.name),
    value: author,
    name: author.name,
    email: author.email,
  };
}

/** Match "Lastname, Firstname". */
function authorFromUser(query) {
  const authorName = query.match(/^(.*),(.*)$/);
  if (!authorName || authorName.length !== 3) {
    return null;
  }
  return formAuthor({
    name:
      _capitalize(authorName[1].trim()) +
      ", " +
      _capitalize(authorName[2].trim()),
  });
}

/** People and e-groups of the CERN directory. */
export function autocompleteAuthors(url, extraParams) {
  return autocomplete(
    url,
    (query) => {
      const userInput = authorFromUser(query);
      const search = userInput ? userInput.name : query;
      return { query: stripCommas(search), ...(extraParams || {}) };
    },
    (response, query) => {
      const userInput = authorFromUser(query);
      const suggestions = response.data.map((hit) => {
        const valueObj = {};
        if (hit.cernAccountType) {
          valueObj.name = hit.sn + ", " + hit.givenName;
          valueObj.ids = [];
          if (Object.prototype.hasOwnProperty.call(hit, "employeeID")) {
            valueObj.ids.push({ value: hit.employeeID, source: "cern" });
          }
        } else {
          valueObj.name = hit.displayName;
        }
        if (hit.cernInstituteName) {
          valueObj.affiliations = [hit.cernInstituteName];
        }
        if (hit.mail) {
          valueObj.email = hit.mail;
        }
        return formAuthor(valueObj);
      });
      prependUserInput(userInput, suggestions);
      return suggestions;
    },
    50
  );
}

/** E-groups and people for the access fields (``autocompleteAccess``). */
export function autocompleteAccess(query) {
  const userInput = query.length
    ? [{ name: query, email: query, isUserInput: true }]
    : [];
  return autocompleteAuthors("/api/ldap/cern-egroups/")(query).then(
    (results) =>
      userInput.concat(
        results.map((res) => ({
          name: res.value.name,
          email: res.value.email,
          isUserInput: false,
        }))
      ),
    () => userInput
  );
}
