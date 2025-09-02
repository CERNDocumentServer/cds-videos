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
import { WebVTT } from "vtt.js";

import { getCookie } from "../getCookie";

// Controllers

/**
 * @ngdoc controller
 * @name cdsRecordController
 * @namespace cdsRecordController
 * @description
 *    CDS record controller.
 */
function cdsRecordController($scope, $sce, $http, $timeout, $filter) {
  // Parameters

  // Assign the controller to `vm`
  var vm = this;

  // Record Loading - If the cdsRecord has the state loading
  vm.cdsRecordLoading = true;

  // Record Error - if the cdsRecord has any error
  vm.cdsRecordError = null;

  // Record Warn - if the cdsRecord has any warning
  vm.cdsRecordWarning = null;

  $scope.transcriptsByLanguage = {};
  $scope.transcript = [];
  $scope.filteredTranscript = [];
  $scope.selectedTranscriptLanguage = null;
  $scope.transcriptSearch = "";
  $scope.chapters = [];
  $scope.activeTab = "chapters"; // Default to chapters tab
  $scope.shortDescription = "";
  $scope.fullDescription = "";

  const REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCookie("csrftoken"),
  };

  $scope.scrollToElement = function (id) {
    setTimeout(function () {
      const el = document.getElementById(id);
      if (el) {
        const rect = el.getBoundingClientRect();
        const isVisible =
          rect.top >= 0 &&
          rect.bottom <=
            (window.innerHeight || document.documentElement.clientHeight);

        if (!isVisible) {
          const topOffset = rect.top + window.scrollY - 60; // adjust for sticky header
          window.scrollTo({ top: topOffset, behavior: "smooth" });
        }
      } else {
        console.warn("Element not found:", id);
      }
    }, 100);
  };

  $scope.seekTo = function (timecode) {
    const player = window.top.player;
    if (player) {
      if (timecode < 0 || timecode > player.duration) {
        console.warn("Invalid timecode:", timecode);
        return;
      }
      player.currentTime = timecode;
      if (player.paused) {
        try {
          const playPromise = player.play();
          if (playPromise && playPromise.catch) {
            playPromise.catch(function (err) {
              console.warn("Autoplay might be blocked by the browser:", err);
            });
          }
        } catch (err) {
          console.warn("Error playing video:", err);
        }
      }
    } else {
      console.warn("Player not available");
    }
  };

  $scope.jumpToChapter = function (timecode) {
    $scope.scrollToElement("videoPlayerSection");
    $scope.seekTo(timecode);
  };

  $scope.closeInThisVideoSection = function () {
    $scope.showInThisVideoSection = false;
  };

  $scope.toggleInThisVideo = function (tab) {
    $scope.showInThisVideoSection = true;
    $scope.activeTab = tab;

    // Jump to Transcriptions section
    if ($scope.showInThisVideoSection) {
      $scope.scrollToElement("inThisVideoSection");
    }
  };

  $scope.parseVttFromUrl = function (url, type, lang) {
    fetch(url)
      .then((res) => res.text())
      .then(function (vttText) {
        const parser = new WebVTT.Parser(window, WebVTT.StringDecoder());
        const cues = {};

        parser.oncue = function (cue) {
          cues[cue.text] = {
            start: cue.startTime,
            end: cue.endTime,
            text: cue.text,
          };
        };

        parser.parse(vttText);
        parser.flush();

        $timeout(function () {
          if (type === "transcript") {
            $scope.transcriptsByLanguage[lang] = cues;

            // Use the first one that loads
            if (!$scope.selectedTranscriptLanguage) {
              $scope.transcript = cues;
              $scope.filterTranscript();
              $scope.selectedTranscriptLanguage = lang;
            }
          } else {
            console.warn("Unknown type for VTT parsing:", type);
          }
        });
      })
      .catch(function (err) {
        console.error("VTT parsing failed", err);
      });
  };

  $scope.filterTranscript = function () {
    var searchTerm = this.transcriptSearch.toLowerCase();
    $scope.filteredTranscript = Object.values($scope.transcript).filter(
      function (line) {
        return (
          !searchTerm ||
          (line.text && line.text.toLowerCase().indexOf(searchTerm) !== -1)
        );
      }
    );
  };

  $scope.$watch("transcript", function (newVal) {
    if (newVal) $scope.filterTranscript();
  });

  $scope.$watch("record", function (newVal) {
    if (newVal) {
      $scope.initVttLoad(newVal);
      $scope.prepareDescriptions(newVal.metadata.description);
    }
  });

  $scope.prepareDescriptions = function (description) {
    if (!description) {
      $scope.shortDescription = "No description";
      $scope.fullDescription = "No description";
      return;
    }

    const lines = description.split(/\r?\n/);
    const firstTen = lines.slice(0, $scope.DESCRIPTION_PREVIEW_LINES).join("\n");

    $scope.shortDescription = $scope.processDescriptionWithClickableTimestamps(firstTen);
    $scope.fullDescription = $scope.processDescriptionWithClickableTimestamps(description);
  };

  $scope.initVttLoad = function (record) {
    const files = record.metadata._files || [];

    // Subtitles (transcripts)
    const transcriptVttFiles = files.filter(
      (f) => f.context_type === "subtitle" && f.content_type === "vtt"
    );

    // Step 2: If found, load it
    transcriptVttFiles.forEach((file) => {
      const lang = file.tags.language || "unknown";
      if (file.links?.self) {
        $scope.parseVttFromUrl(file.links.self, "transcript", lang);
      } else {
        console.warn("No subtitle file found.");
      }
    });

    // Use chapters from API or parse from description as fallback
    if (record.metadata.chapters && record.metadata.chapters.length > 0) {
      $scope.chapters = record.metadata.chapters;
    }

    // Set default active tab based on what's available (prioritize chapters)
    const hasTranscripts = (record.metadata._files || []).some(
      (f) => f.context_type === "subtitle" && f.content_type === "vtt"
    );

    if ($scope.chapters.length > 0) {
      $scope.activeTab = "chapters";
    } else if (hasTranscripts) {
      $scope.activeTab = "transcript";
    }
  };

  $scope.setTranscriptLanguage = function (lang) {
    if ($scope.transcriptsByLanguage[lang]) {
      $scope.transcript = $scope.transcriptsByLanguage[lang];
      $scope.filterTranscript();
    } else {
      console.warn("Transcript not found for language:", lang);
    }
  };

  function getScrollableParent(el) {
    while (el && el !== document.body) {
      const style = window.getComputedStyle(el);
      const overflowY = style.overflowY;
      if (overflowY === "auto" || overflowY === "scroll") {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  // Follow transcriptions
  $scope.currentTranscriptLine = null;
  function updateTranscriptHighlight() {
    const player = window.top.player;
    if (!player || !$scope.transcript) return;

    const currentTime = player.currentTime;
    const lines = Object.values($scope.transcript);

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (currentTime >= line.start && currentTime <= line.end) {
        if ($scope.currentTranscriptLine !== line) {
          $scope.currentTranscriptLine = line;
          $scope.$applyAsync(); // Trigger Angular update

          // Auto-scroll to the active line
          setTimeout(() => {
            const el = document.querySelector(".transcript-line.active");
            const container = getScrollableParent(el);

            if (el && container) {
              const elRect = el.getBoundingClientRect();
              const containerRect = container.getBoundingClientRect();

              const currentScroll = container.scrollTop;
              const topOffset = elRect.top - containerRect.top;

              const targetScroll = currentScroll + topOffset - 10;

              container.scrollTo({
                top: targetScroll,
                behavior: "smooth",
              });
            }
          }, 50);
        }
        return;
      }
    }

    $scope.currentTranscriptLine = null;
    $scope.$applyAsync();
  }

  $scope.currentChapter = null;
  function updateChapterHighlight() {
    const player = window.top.player;
    if (!player || !$scope.chapters || $scope.chapters.length === 0) return;

    const currentTime = player.currentTime;

    for (let i = 0; i < $scope.chapters.length; i++) {
      const chapter = $scope.chapters[i];
      const nextChapter = $scope.chapters[i + 1];

      // If current time is within this chapter range
      if (
        currentTime >= chapter.seconds &&
        (!nextChapter || currentTime < nextChapter.seconds)
      ) {
        if ($scope.currentChapter !== chapter) {
          $scope.currentChapter = chapter;
          $scope.$applyAsync();

          // Auto-scroll to active chapter
          setTimeout(() => {
            const el = document.querySelector(".chapter-item.active");
            const container = getScrollableParent(el);

            if (el && container) {
              const elRect = el.getBoundingClientRect();
              const containerRect = container.getBoundingClientRect();
              const currentScroll = container.scrollTop;
              const topOffset = elRect.top - containerRect.top;
              const targetScroll = currentScroll + topOffset - 10;

              container.scrollTo({
                top: targetScroll,
                behavior: "smooth",
              });
            }
          }, 50);
        }
        return;
      }
    }

    // No chapter active
    $scope.currentChapter = null;
    $scope.$applyAsync();
  }

  let transcriptTimer = setInterval(updateTranscriptHighlight, 100);
  let chapterTimer = setInterval(updateChapterHighlight, 100);

  $scope.$on("$destroy", function () {
    clearInterval(transcriptTimer);
    clearInterval(chapterTimer);
  });

  $scope.convertToMinutesSeconds = function (seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);

    // Pad with zero if needed
    const paddedSecs = secs < 10 ? "0" + secs : secs;

    return `${minutes}:${paddedSecs}`;
  };

  $scope.setActiveTab = function (tab) {
    $scope.activeTab = tab;
  };

  $scope.processDescriptionWithClickableTimestamps = function (description) {
    if (!description) return description;

    // Regex pattern to match timestamp formats: 0:00, 00:00, 0:00:00, 00:00:00
    const pattern = /(\d{1,2}:(?:\d{1,2}:)?\d{1,2})/g;

    return description.replace(pattern, function (match) {
      // Parse timestamp to seconds for the seek function
      const timeParts = match.split(":");
      let totalSeconds;

      if (timeParts.length === 2) {
        const [minutes, seconds] = timeParts.map(Number);
        totalSeconds = minutes * 60 + seconds;
      } else if (timeParts.length === 3) {
        const [hours, minutes, seconds] = timeParts.map(Number);
        totalSeconds = hours * 3600 + minutes * 60 + seconds;
      } else {
        return match; // Return unchanged if invalid format
      }

      // Return clickable timestamp using onclick for ng-bind-html compatibility
      return `<a href="javascript:void(0)" class="timestamp-link" onclick="(function(){ try { angular.element(document.querySelector('.cds-detail-description')).scope().jumpToChapter(${totalSeconds}); } catch(e) { console.error('Could not seek to timestamp:', e); } })()" style="color: #2196F3; font-weight: 600; cursor: pointer;">${match}</a>`;
    });
  };

  $scope.getChapterFrame = function (chapter) {
    if (!$scope.record || !chapter) return null;

    // Use the findMaster filter to get the master file (this filter is defined in cds/module.js)
    const master = $filter("findMaster")($scope.record);

    if (!master || !master.frame) return null;

    // Look for a frame with filename that matches chapter timestamp
    // Chapter frames are named like "chapter-{seconds}.jpg"
    const expectedFrameName = `chapter-${chapter.seconds}.jpg`;

    let chapterFrame = master.frame.find(
      (frame) => frame.key === expectedFrameName
    );
    if (!chapterFrame) {
      // Find the frame with closest timestamp
      const target = Number(chapter.seconds);
      let closest = null;
      let minDiff = Infinity;

      master.frame.forEach((frame) => {
        if (!frame.tags || frame.tags.timestamp == null) return;

        const ts = Number(frame.tags.timestamp);

        const diff = Math.abs(ts - target);
        if (diff < minDiff) {
          minDiff = diff;
          closest = frame;
        }
      });

      chapterFrame = closest;
    }

    return chapterFrame || null;
  };

  $scope.cleanHtmlFromTitle = function (title) {
    if (!title) return title;

    // Remove HTML tags and clean up whitespace for display purposes only
    let cleanTitle = title.replace(/<[^>]+>/g, " ");
    cleanTitle = cleanTitle.replace(/\s+/g, " ").trim();

    return cleanTitle;
  };

  $scope.share = {
    link: window.location.href.split("?")[0],
    startInput: "0:00",
    withStart: false,
  };

  function parseHMS(txt) {
    if (txt == null) return NaN;
    txt = String(txt).trim();
    if (!txt) return NaN;
    if (!/^\d{1,2}(?::\d{1,2}){0,2}$/.test(txt)) return NaN;

    var parts = txt.split(":").map(Number);
    if (parts.length === 1) return parts[0]; // ss
    if (parts.length === 2) return parts[0] * 60 + parts[1]; // mm:ss
    return parts[0] * 3600 + parts[1] * 60 + parts[2]; // hh:mm:ss
  }

  $scope.updateShareLink = function () {
    var url = window.location.href.split("?")[0];
    if ($scope.share.withStart) {
      var secs = parseHMS($scope.share.startInput);
      if (!isNaN(secs) && secs > 0) {
        url += (url.indexOf("?") === -1 ? "?" : "&") + "t=" + Math.floor(secs);
      }
    }
    $scope.share.link = url;
  };

  $scope.copyShareLink = function () {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText($scope.share.link);
    } else {
      var tmp = document.createElement("textarea");
      tmp.value = $scope.share.link;
      document.body.appendChild(tmp);
      tmp.select();
      try {
        document.execCommand("copy");
      } catch (e) {}
      document.body.removeChild(tmp);
    }
  };


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

    var replacedUrl = replaceMediaDownloadUrlParams(
      $scope.mediaDownloadEventUrl,
      $scope.record.metadata
    );

    $http
      .post(
        replacedUrl,
        {
          key: fileObj.key,
        },
        { headers: REQUEST_HEADERS }
      )
      .then(function (response) {})
      .then(function (error) {});
  };

  function replaceMediaDownloadUrlParams(url, recordMetadata) {
    return url.replace("{recid}", recordMetadata.recid);
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

cdsRecordController.$inject = [
  "$scope",
  "$sce",
  "$http",
  "$timeout",
  "$filter",
];

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

    scope.relatedQueryUrl = attrs.relatedQueryUrl;

    scope.DESCRIPTION_PREVIEW_LINES = parseInt(attrs.previewLines, 10) || 10;

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
        scope.recordViews = response.data.views;
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

angular.module("cdsRecord.directives", []).directive("cdsRecordView", cdsRecordView);

angular
  .module("cdsRecord.controllers", [])
  .controller("cdsRecordCtrl", cdsRecordController);

angular.module("cdsRecord", ["cdsRecord.controllers", "cdsRecord.directives"]);
