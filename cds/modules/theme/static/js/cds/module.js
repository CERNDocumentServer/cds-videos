/*
 * This file is part of Invenio.
 * Copyright (C) 2016, 2017, 2018 CERN.
 *
 * Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

* In applying this license, CERN does not
* waive the privileges and immunities granted to it by virtue of its status
* as an Intergovernmental Organization or submit itself to any jurisdiction.
*/

var app = angular.module('cds', [
  'ngclipboard',
  'ui.bootstrap.dropdown',
  'ui.bootstrap.tooltip',
  'ui.bootstrap.popover',
  'ui.bootstrap.alert',
]);


// Image loading with fallback
app.directive('cdsSearchResults', ['$sce', '$window', function($sce, $window) {
  function linkFunction(scope, element, attr) {
    // Find poster
    scope.findPoster = function(record) {
      var poster = scope.findContextType(record, 'poster');
      if (poster) {
        return poster;
      } else {
        var masterFile = scope.findContextType(record, 'master');
        return _.find(masterFile['frame'], function (frame) {
          return frame.key === 'frame-1.jpg'
        })
      }
    }
    // Find gif
    scope.findGif = function(record) {
      var masterFile = scope.findContextType(record, 'master');
      return _.find(masterFile['frames-preview'], function (gif) {
        return gif.key === 'frames.gif'
      })
    }
    // Find context type
    scope.findContextType = function(record, context_type) {
      if (!_.isEmpty(record)) {
        var _files = record.metadata ? record.metadata._files : record._files;
        return _.find(_files, function (file) {
          return file.context_type === context_type;
        })
      }
    }
    // Get image preview
    scope.getImagePreview = function(record, showGif, size) {
      try {
        var file = showGif ? scope.findGif(record) : scope.findPoster(record);
        return _.template(
          "/api/iiif/v2/<%=bucket%>:<%=version_id%>:<%=key%>/full/!<%=size%>/0/default.<%=ext%>"
        )({
          bucket: file.bucket_id,
          key: file.key,
          version_id: file.version_id,
          size: size.join(','),
          ext: showGif ? 'gif' : 'png',
        });
      } catch(error) {
        return '/static/img/not_found.png';
      }
    }
  }
  return {
    restrict: 'A',
    link: linkFunction
  };
}])

app.run(function($templateCache) {
  // Template Cache for bootstrap tooltip
  $templateCache.put(
    'uib/template/tooltip/tooltip-html-popup.html',
    '<div class="tooltip-arrow"></div>' +
    '<div class="tooltip-inner" ng-bind-html="contentExp()"></div>'
  );
  // Template Cache for bootstrap popover
  $templateCache.put(
    'uib/template/popover/popover-html.html',
    '<div class="arrow"></div>' +
    '<div class="popover-inner">' +
    '<h3 class="popover-title" ng-bind="uibTitle" ng-if="uibTitle"></h3>' +
    '<div class="popover-content" ng-bind-html="contentExp()"></div>' +
    '</div>'
  );
  // Template Cache for bootstrap alert
  $templateCache.put(
    'uib/template/alert/alert.html',
    '<button ng-show="closeable" type="button" class="close" ng-click="close({$event: $event})">' +
    '<span aria-hidden="true">&times;</span>' +
    '<span class="sr-only">Close</span>' +
    '</button>' +
    '<div ng-transclude></div>'
  );
});

app.filter('previewIframe', ['$sce', '$window', function($sce, $window) {
  return function(text, reportNumber, external) {
    var _url = '/video/' + reportNumber;
    if (external) {
      _url = $window.location.origin + _url;
    }
    var iframe = _.template(
      '<iframe scrolling="no"  src="<%= src %>" width="560" height="315"' +
      ' frameborder="0" allowfullscreen></iframe>'
    );
    return iframe({
      src: $sce.trustAsResourceUrl(_url)
    });
  };
}]);

app.directive('errSrc', function() {
  // Replace 404 images with an error
  return {
    link: function(scope, element, attrs) {
      element.bind('error', function() {
        if (attrs.src != attrs.errSrc) {
          attrs.$set('src', attrs.errSrc);
        }
      });
    }
  }
});

app.filter('previewIframeSrc', ['$sce', '$window', function($sce, $window) {
  return function(text, id, key, external) {
    var _url = '/record/' + id + '/preview/' + key;
    if (external) {
      _url = $window.location.origin + _url;
    }
    return $sce.trustAsResourceUrl(_url)
  };
}]);

app.filter('isEmpty', function() {
  return function(text) {
    return _.isEmpty(text);
  };
});

app.filter('toInt', function() {
  return function(text) {
    return text ? parseInt(text) : text;
  }
});

app.filter('toMinutes', function() {
  return function(seconds) {
    try {
      return new Date(seconds * 1000).toISOString().substr(11, 8);
    } catch(error) {
      return seconds
    }
  }
});

app.filter('findBy', function() {
  return function(data, key, value) {
    if (!_.isEmpty(data)) {
      return _.filter(data, _.matchesProperty(key, value));
    }
  }
});

app.filter('removeBy', function() {
  return function(data, key, value) {
    if (!_.isEmpty(data)) {
      return _.reject(data, _.matchesProperty(key, value));
    }
  }
});

// Find record's file with given context_type
app.filter('findContextType', function() {
  return function(record, context_type) {
    if (!_.isEmpty(record)) {
      var _files = record.metadata ? record.metadata._files : record._files;
      return _.find(_files, function (file) {
        return file.context_type === context_type;
      })
    }
  }
});

// Find master video file in record's files
app.filter('findMaster', function($filter) {
  return function(record) {
    return $filter('findContextType')(record, 'master');
  }
});

// Find closest video resolution
app.filter('findResolution', function($filter) {
  return function(record) {
    var height = parseInt(record['tags']['height'], 10);
    var width = parseInt(record['tags']['width'], 10);

    var selectedResolution = height.toString().concat('p');

    var heightsToQualities = {
      240: '240p',
      360: '360p',
      480: '480p',
      720: '720p',
      1024: '1024p',
      1080: 'TBD',
      2160: '4K',
      4320: '8K'
    };

    Object.keys(heightsToQualities).forEach(function(resolution) {
      if (height >= resolution) {
        selectedResolution = heightsToQualities[resolution];
      }
    });

    if (selectedResolution === 'TBD') {
      var widthToQualities = {
        1920: '1080p',
        2048: '2K'
      };

      // default case with first value
      selectedResolution = widthToQualities[1920];

      Object.keys(widthToQualities).forEach(function(resolution) {
        if (width >= resolution) {
          selectedResolution = widthToQualities[resolution];
        }
      });
    }

    return selectedResolution;
  }
});

// Find first frame of master video file
app.filter('findPoster', function($filter) {
  return function(record) {
    var poster = $filter('findContextType')(record, 'poster');
    if (poster) {
      return poster;
    } else {
      var masterFile = $filter('findMaster')(record);
      return _.find(masterFile['frame'], function (frame) {
        return frame.key === 'frame-1.jpg';
      })
    }
  }
});

// Find gif animation of master video file's frames
app.filter('findGif', function() {
  return function(masterFile) {
    return _.find(masterFile['frames-preview'], function (gif) {
      return gif.key === 'frames.gif';
    })
  }
});

// Get FlaskIIIF resize link
app.filter('iiif', function($filter) {
  return function(record, showGif, size) {
    try {
      var masterFile = $filter('findMaster')(record);
      console.log(masterFile);
      var filterFun = showGif ? 'findGif' : 'findPoster';
      var filterArg = showGif ? masterFile : record
      return _.template(
        "/api/iiif/v2/<%=bucket%>:<%=version_id%>:<%=key%>/full/!<%=size%>/0/default.<%=ext%>"
      )({
        bucket: masterFile.bucket_id,
        key: $filter(filterFun)(filterArg).key,
        version_id: masterFile.version_id,
        size: size.join(','),
        ext: showGif ? 'gif' : 'png',
      });
    } catch(error) {
      return '/static/img/not_found.png';
    }

  }
});

app.filter('ellipsis', function () {
  return function (text, length) {
      if (text.length > length) {
          return text.substr(0, length) + " [...]";
      }
      return text;
  }
});

// Trust as html
app.filter('trustHtml', ['$sce', function($sce) {
  return function(text) {
    return $sce.trustAsHtml(text);
  };
}]);

// Group by key filter
app.filter('groupBy', function() {
  return _.memoize(function(items, field, defaultGroup) {
    return _.groupBy(items, function(e) {
      return _.get(e, field) || defaultGroup;
    })
  });
});

// Downloadable files - files for download and files for additonal
app.filter('groupDownloadable', function() {
  return _.memoize(function(items, field, defaultGroup) {
    return _.groupBy(items, function(e) {
      return _.get(e, 'tags.download')  === 'true' ?  'download' : 'additional';
    })
  });
});

// Sort video subformats descending by height
app.filter('sortVideosDescending', function() {
  return function(videos) {
    return _.orderBy(videos, function(video) {
      return parseInt(video.tags.height);
    }, ['desc']);
  }
});

/**
 * Gett all files with types passed as argument
 * @param {Array} files
 * @param {Array} types the context type of a file
 *
 * ex:
 * data.files | getFilesByType: ['subtitle']
 * The function will filter all the files with the 'context_type' 'subtitle'
 */
app.filter('getFilesByType', function() {
  return function(files, types) {
    if (!_.isArray(files) || !_.isArray(types) || !types.length || !files.length) { return files; }

    return files.filter(function(file) {
      return types.indexOf(file.context_type) !== -1;
    });
  }
});

/**
 * Gett all files except the the files with types passed as argument
 * @param {Array} files
 * @param {Array} types the context type of a file
 *
 * ex:
 * data.files | getAllFilesExcept: ['subtitle']
 * The function will filter all the files that have the 'context_type' not equal to 'subtitle'
 */
app.filter('getAllFilesExcept', function() {
  return function(files, types) {
    if (!_.isArray(files) || !_.isArray(types) || !types.length || !files.length) { return files; }

    return files.filter(function(file) {
      return types.indexOf(file.context_type) == -1;
    });
  }
});

// Transform the URL into absolute an URL
app.filter('absoluteURL', ['$sce', function($sce) {
  return function(url) {
    if (url.startsWith("https://") || url.startsWith("http://")) {
        // The protocol is correct
        return url;
    } else {
      // The URL is: 'foo.com' or 'www.foo.com', so at least add the http
        return  "http://" + url;
    }
  };
}]);

// Truncate words
app.filter('wordsSplit', function () {
  return function (input, words) {
      if (words === undefined) return input;
      if (words <= 0) return '';
      if (input) {
          var inputWords = input.split(/\s+/);
          if (inputWords.length > words) {
              input = inputWords.slice(0, words).join(' ') + ' [...]';
          }
      }
      return input;
  };
});

app.filter('isPublic', function () {
  return function (record) {
    return (_.get(record, '_access') === undefined || _.get(record, '_access.read') === undefined || _.get(record, '_access.read').length == 0);
  };
});
// Image loading with fallback
app.directive('imageProgressiveLoading', ['$timeout', function($timeout) {

  // Load image async
  function loadImage(src) {
    return new Promise(function(resolve, reject) {
      var _img = new Image();
      _img.src = src;
      _img.onload = function() {
        return resolve(src);
      };
      _img.onerror = function() {
        return reject(src);
      }
    })
  }

  function linkFunction(scope, element, attr){
    var timer;
    element.addClass('cds-blur');
    // Is the image loaded
    scope.isLoaded = false;
    // Is the gif loaded
    scope.isGifLoaded = false;
    // Has gif error
    scope.hasGifError = false;
    // Has image error
    scope.hasImageError = false;
    // Is over the element
    scope.isOverTheElement = false;
    // Element mouseover listener
    var mouseOverListener = null;

    // Replace the blurred image with the actual image
    loadImage(attr.imgSrc)
      .then(
        function(src) {
          // The image has been loaded
          scope.isLoaded = true;
          element[0].src = src;
          attr.$set('src', src);
          element.removeClass('cds-blur');
        },
        function() {
          scope.hasImageError = true;
        }
      );
      // If there is a gif then
      if (attr.gifSrc) {
        // When the mouse is out of the element
        element.bind('mouseleave', function() {
          // Mouse left the element
          scope.isOverTheElement = false;
          // Return back the image
          element[0].src = attr.imgSrc;
          attr.$set('src', attr.imgSrc);
        });
        // When the mouse is over the  element
        element.bind('mouseover', function() {
          if (!scope.hasGifError) {
            // Mouse is over the element
            scope.isOverTheElement = true;
            if (!scope.isGifLoaded) {
              loadImage(attr.gifSrc)
                .then(
                  function() {
                    scope.isGifLoaded = true;
                    // Check if the user is still Waiting
                    if (scope.isOverTheElement) {
                      // Put the gif up
                      element[0].src = attr.gifSrc;
                      attr.$set('src', attr.gifSrc);
                    }
                  },
                  function() {
                    // Gif error
                    scope.hasGifError = true;
                  }
                )
            } else {
              // Put the gif up
              element[0].src = attr.gifSrc;
              attr.$set('src', attr.gifSrc);
            }
          }
        });
      }
  }
  return {
      restrict: 'A',
      link: linkFunction
  };
}])

// Filter to translage ISO languages to language name
// i.e. en -> English , fr -> French
app.filter('isoToLanguage', ['isoLanguages', function (isoLanguages) {
  return function (code) {
    return isoLanguages[code] || code;
  };
}]);

// Join array or return the String
app.filter('joinArray', function () {
  return function (item) {
    if (_.isArray(item)) {
      return item.join(', ');
    }
    return item;
  }
});

// String duration ``.000``
app.filter('replace', function () {
  return function (text, replaceText, replaceWith) {
    if (text) {
      return text.replace(replaceText, replaceWith);
    }
  }
});

// replace '_' with ' '
app.filter('titlecase', function () {
  return function (text, replaceText, replaceWith) {
    return text ? String(text).replace(/_/g, ' ') : '';
  }
});

app.provider('isoLanguages', function () {
  return {
    $get: function () {
      // Based on https://www.loc.gov/standards/iso639-2/php/code_list.php
      return {
        'ar': 'Arabic',
        'bg': 'Bulgarian',
        'ca': 'Catalan',
        'ch': 'Chamorro',
        'cs': 'Czech',
        'da': 'Danish',
        'de': 'German',
        'el': 'Greek',
        'en': 'English',
        'en-fr': 'English/French',
        'es': 'Spanish',
        'fi': 'Finnish',
        'fr': 'French',
        'hr': 'Croatian',
        'hu': 'Hungarian',
        'it': 'Italian',
        'ja': 'Japanese',
        'ka': 'Georgian',
        'ko': 'Korean',
        'nl': 'Dutch',
        'no': 'Norwegian',
        'pl': 'Polish',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'silent': 'Silent',
        'sk': 'Slovak',
        'sr': 'Serbian',
        'sv': 'Swedish',
        'tr': 'Turkish',
        'uk': 'Ukrainian',
        'zh_CN': 'Chinese',
        'zh_TW': 'Chinese (Taiwan)',
      };
    }
  }
});

// Directive for bootstrap popover to work inside ng-repeat
app.directive('popover', function () {
  return function (scope, element, attrs) {
    element.find('a[rel=popover]').popover();
  };
});

// Filter to format urls for download
app.filter('download', function () {
  return function(url) {
    // Check if the url is invalid
    if (!url) { return url; }

    re = /([?&].*)=[^?&]+/;
    // Check if the url has a querystring
    if (url.match(re)) {
      return url + '&download';
    }

    return url + '?download';
  }
});

// filter for sharing on different social platforms
// more details about how we build the URLs you can find on: https://github.com/bradvin/social-share-urls
app.filter('assembleShareURL', ['$window', function($window) {
  return function(record, platform) {
    if (!record) { return; }

    var title = encodeURIComponent(record.metadata.title.title);
    var description = encodeURIComponent(record.metadata.description);
    var currentPageAddress = encodeURIComponent($window.location.href);

    var platformMapping = {
      'facebook': 'https://www.facebook.com/sharer.php?u=' + currentPageAddress,
      'twitter': 'https://twitter.com/intent/tweet?url=' + currentPageAddress + '&text=' + title + '&hashtags=cern',
      'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + currentPageAddress + '&title=' + title + '&summary=' + description + '&source=' + currentPageAddress,
      'reddit': 'https://reddit.com/submit?url=' + currentPageAddress + '&title=' + title,
      'email': 'mailto:?subject=' + title + '&body=' + description + '%0a' + currentPageAddress,
    };

    return platformMapping[platform];
  };
}]);
