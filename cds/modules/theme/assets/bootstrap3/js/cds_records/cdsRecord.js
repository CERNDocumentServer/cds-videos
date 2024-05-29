/*
 * This file is part of CERN Document Server.
 * Copyright (C) 2016 CERN.
 *
 * CERN Document Server is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * CERN Document Server is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with CERN Document Server; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 *
 * In applying this license, CERN does not
 * waive the privileges and immunities granted to it by virtue of its status
 * as an Intergovernmental Organization or submit itself to any jurisdiction.
 */

/*******
 * Moved from https://github.com/CERNDocumentServer/cds-js/blob/master/src/cds/record/module.js
 */

import angular from "angular";

// Controllers

/**
 * @ngdoc controller
 * @name cdsRecordController
 * @namespace cdsRecordController
 * @description
 *    CDS record controller.
 */
function cdsRecordController($scope, $sce, $http) {
  // Parameters

  // Assign the controller to `vm`
  var vm = this;

  // Record Loading - If the cdsRecord has the state loading
  vm.cdsRecordLoading = true;

  // Record Error - if the cdsRecord has any error
  vm.cdsRecordError = null;

  // Record Warn - if the cdsRecord has any warning
  vm.cdsRecordWarning = null;

  ////////////

  // Functions

  /**
   * Trust iframe url
   * @memberof cdsRecordController
   * @function cdsRecordIframe
   * @param {String} url - The url.
   */
  function cdsRecordIframe(url) {
    // Return the trusted url
    return $sce.trustAsResourceUrl(url);
  }

  /**
   * When the module initialized
   * @memberof cdsRecordController
   * @function cdsRecordInit
   * @param {Object} evt - The event object.
   */
  function cdsRecordInit(evt) {
    // Stop loading
    vm.cdsRecordLoading = false;
  }

  /**
   * Change the state to loading
   * @memberof cdsRecordController
   * @function cdsRecordLoadingStart
   * @param {Object} evt - The event object.
   */
  function cdsRecordLoadingStart(evt) {
    // Set the state to loading
    vm.cdsRecordLoading = true;
  }

  /**
   * Change the state to normal
   * @memberof cdsRecordController
   * @function cdsRecordLoadingStop
   * @param {Object} evt - The event object.
   */
  function cdsRecordLoadingStop(evt) {
    // Set the state to normal
    vm.cdsRecordLoading = false;
  }

  /**
   * Show error messages
   * @memberof cdsRecordController
   * @function cdsRecordError
   * @param {Object} evt - The event object.
   * @param {Object} error - The object with the errors.
   */
  function cdsRecordError(evt, error) {
    // Reset the error
    vm.cdsRecordError = null;
    // Attach the error to the scope
    vm.cdsRecordError = error;
  }

  /**
   * Show warning messages
   * @memberof cdsRecordController
   * @function cdsRecordWarn
   * @param {Object} evt - The event object.
   * @param {Object} warning - The object with the warnings.
   */
  function cdsRecordWarn(evt, warning) {
    // Reset the error
    vm.cdsRecordWarning = null;
    // Attach the warning to the scope
    vm.cdsRecordWarning = warning;
  }

  $scope.logMediaDownload = function (fileObj) {
    if (!$scope.mediaDownloadEventUrl) {
      return;
    }

    var quality =
        fileObj.context_type === "master"
          ? "master"
          : fileObj.tags.preset_quality,
      replacedUrl = replaceMediaDownloadUrlParams(
        $scope.mediaDownloadEventUrl,
        $scope.record.metadata,
        fileObj.key,
        quality
      );

    $http
      .get(replacedUrl)
      .then(function (response) {})
      .then(function (error) {});
  };

  function replaceMediaDownloadUrlParams(
    url,
    recordMetadata,
    filename,
    quality
  ) {
    var reportNumber =
        recordMetadata.hasOwnProperty("report_number") &&
        recordMetadata.report_number instanceof Array &&
        recordMetadata.report_number.length > 0
          ? recordMetadata.report_number[0]
          : "",
      filenameParts = filename.split("."),
      filenamePartsCount = filenameParts.length,
      fileFormat =
        filenamePartsCount > 1 ? filenameParts[filenamePartsCount - 1] : "";

    return url
      .replace("{recid}", recordMetadata.recid)
      .replace("{report_number}", reportNumber)
      .replace("{format}", fileFormat)
      .replace("{quality}", quality);
  }

  ////////////

  // Assignements

  // Iframe src
  vm.iframeSrc = cdsRecordIframe;

  ////////////

  // Listeners

  // When the module initialized
  $scope.$on("cds.record.init", cdsRecordInit);

  // When there is an error
  $scope.$on("cds.record.error", cdsRecordError);
  // When there is a warning
  $scope.$on("cds.record.warn", cdsRecordWarn);

  // When loading requested to start
  $scope.$on("cds.record.loading.start", cdsRecordLoadingStart);
  // When loading requested to stop
  $scope.$on("cds.record.loading.stop", cdsRecordLoadingStop);
}

cdsRecordController.$inject = ["$scope", "$sce", "$http"];

////////////

// Directives

/**
 * @ngdoc directive
 * @name cdsRecordView
 * @description
 *    The cdsRecordView directive
 * @namespace cdsRecordView
 * @example
 *    Usage:
 *    <cds-record-view
 *     template='TEMPLATE_PATH'>
 *    </cds-record-view>
 */
function cdsRecordView($http) {
  // Functions

  /**
   * Force apply the attributes to the scope
   * @memberof cdsRecordView
   * @param {service} scope -  The scope of this element.
   * @param {service} element - Element that this direcive is assigned to.
   * @param {service} attrs - Attribute of this element.
   * @param {cdsRecordCtrl} vm - CERN Document Server record controller.
   */
  function link(scope, element, attrs, vm) {
    scope.mediaDownloadEventUrl = attrs.mediaDownloadEventUrl;

    // Get the record object and make it available to the scope
    $http.get(attrs.record).then(
      function (response) {
        scope.record = response.data;
        scope.$broadcast("cds.record.init");
      },
      function (error) {
        scope.$broadcast("cds.record.error", error);
      }
    );

    // Get the number of views for the record and make it available to the scope
    $http.get(attrs.recordViews).then(
      function (response) {
        scope.recordViews = response.data;
      },
      function (error) {
        scope.$broadcast("cds.record.error", error);
      }
    );
  }

  /**
   * Choose template for search bar
   * @memberof cdsRecordView
   * @param {service} element - Element that this direcive is assigned to.
   * @param {service} attrs - Attribute of this element.
   * @example
   *    Minimal template `template.html` usage
   *    {{ record.title_statement.title }}
   */
  function templateUrl(element, attrs) {
    return attrs.template;
  }

  ////////////

  return {
    restrict: "AE",
    scope: false,
    controller: "cdsRecordCtrl",
    controllerAs: "vm",
    link: link,
    templateUrl: templateUrl,
  };
}

cdsRecordView.$inject = ["$http"];

////////////

// Setup everything

angular
  .module("cdsRecord.directives", [])
  .directive("cdsRecordView", cdsRecordView);

angular
  .module("cdsRecord.controllers", [])
  .controller("cdsRecordCtrl", cdsRecordController);

angular.module("cdsRecord", ["cdsRecord.controllers", "cdsRecord.directives"]);
