import angular from "angular";
import _ from "lodash";

function cdsVideoListCtrl($scope, $timeout) {
  var that = this;
  
  // State management for video list
  this.selectedVideoId = null;
  this.expandedVideoId = null;
  this.loadingVideo = null;
  
  // Filter state
  this.statusFilter = 'all'; // 'all', 'published', 'draft'
  
  // Performance optimization: cache computed values
  this._statusCache = new Map();
  this._titleCache = new Map();
  this._thumbnailCache = new Map();
  
  // Clear cache when videos change
  var clearCache = function() {
    that._statusCache.clear();
    that._titleCache.clear();
    that._thumbnailCache.clear();
  };
  
  // Initialize component
  this.$onInit = function() {
    // Auto-select and expand first video if available
    if (that.videos && that.videos.length > 0) {
      that.selectedVideoId = that.videos[0]._deposit.id;
      // Auto-expand first video after a short delay
      $timeout(function() {
        that.expandedVideoId = that.videos[0]._deposit.id;
      }, 100);
    }
    
    // Listen for deposit status changes to clear cache and update UI
    $scope.$on("cds.deposit.status.changed", function(event, statusData) {
      if (statusData && statusData.depositId) {
        // Clear cache for the specific video that had status changes
        that._statusCache.delete(statusData.depositId);
        that._titleCache.delete(statusData.depositId);
        that._thumbnailCache.delete(statusData.depositId);
        
        // Force UI update by triggering digest cycle
        $scope.$applyAsync();
      }
    });
    
    // Listen for metadata updates which can also affect status display
    $scope.$on("cds.deposit.metadata.update", function(event, data) {
      // Clear all cache when metadata updates occur
      clearCache();
      $scope.$applyAsync();
    });
    
    // Listen for polling updates to ensure UI synchronization
    $scope.$on("cds.deposit.polling.update", function(event, pollingData) {
      if (pollingData && pollingData.depositId) {
        // Clear cache for the specific video during polling to ensure fresh status
        that._statusCache.delete(pollingData.depositId);
      }
    });
    
    // Listen for video deletion events to update UI
    $scope.$on("cds.video.deleted", function(event, deletionData) {
      if (deletionData && deletionData.videoId) {
        // Clear cache for the deleted video
        that._statusCache.delete(deletionData.videoId);
        that._titleCache.delete(deletionData.videoId);
        that._thumbnailCache.delete(deletionData.videoId);
        
        // If the deleted video was selected, clear selection
        if (that.selectedVideoId === deletionData.videoId) {
          that.selectedVideoId = null;
          that.expandedVideoId = null;
          
          // Auto-select first remaining video if any
          if (that.videos && that.videos.length > 0) {
            that.selectedVideoId = that.videos[0]._deposit.id;
            $timeout(function() {
              that.expandedVideoId = that.videos[0]._deposit.id;
            }, 100);
          }
        }
        
        // Remove from expanded descriptions set
        that.expandedDescriptions.delete(deletionData.videoId);
        
        // Force UI update
        $scope.$applyAsync();
      }
    });
    
    // Watch for video changes and clear cache
    $scope.$watch('$ctrl.videos', function(newVideos, oldVideos) {
      if (newVideos !== oldVideos) {
        clearCache();
        
        // Handle video addition/removal
        if (newVideos && oldVideos) {
          // Check if new videos were added
          if (newVideos.length > oldVideos.length) {
            // Find the newly added video(s)
            var newVideoIds = newVideos.map(v => v._deposit.id);
            var oldVideoIds = oldVideos.map(v => v._deposit.id);
            var addedVideoIds = newVideoIds.filter(id => !oldVideoIds.includes(id));
            
            // Auto-select the newest added video
            if (addedVideoIds.length > 0) {
              var newestVideoId = addedVideoIds[addedVideoIds.length - 1];
              that.selectedVideoId = newestVideoId;
              $timeout(function() {
                that.expandedVideoId = newestVideoId;
              }, 300);
            }
          }
        }
        
        // Auto-select first video when videos are loaded initially
        if (newVideos && newVideos.length > 0 && !that.selectedVideoId) {
          that.selectedVideoId = newVideos[0]._deposit.id;
          $timeout(function() {
            that.expandedVideoId = newVideos[0]._deposit.id;
          }, 100);
        }
      }
    }, true); // Deep watch to detect array changes
  };
  
  // Select a video from the list
  this.selectVideo = function(videoId) {
    // If clicking on the same video that's already selected and expanded, do nothing
    if (that.selectedVideoId === videoId && that.expandedVideoId === videoId) {
      return;
    }
    
    // If switching to a different video, trigger autosave for the currently expanded video
    if (that.expandedVideoId && that.expandedVideoId !== videoId) {
      $scope.$broadcast("cds.deposit.project.saveAll");
    }
    
    that.selectedVideoId = videoId;
    that.loadingVideo = videoId;
    
    // Small delay to show loading state
    $timeout(function() {
      that.expandedVideoId = videoId;
      that.loadingVideo = null;
      
      // Emit event to notify parent components
      $scope.$emit('cds.video.selected', videoId);
    }, 300);
  };
  
  // Get video status for display (cached)
  this.getVideoStatus = function(video) {
    var videoId = video._deposit.id;
    var cached = that._statusCache.get(videoId);
    if (cached) return cached;
    
    var result;
    if (!video._cds || !video._cds.state) {
      result = { status: 'draft', label: 'Draft', class: 'label-default' };
    } else {
      var state = video._cds.state;
      var anyFailed = Object.values(state).some(s => s === 'FAILURE');
      var anyRunning = Object.values(state).some(s => s === 'STARTED' || s === 'PENDING');
      var allSuccess = Object.values(state).every(s => s === 'SUCCESS');
      
      if (anyFailed) {
        result = { status: 'failed', label: 'Processing Failed', class: 'label-danger' };
      } else if (anyRunning) {
        result = { status: 'processing', label: 'Processing', class: 'label-warning' };
      } else if (allSuccess) {
        result = { status: 'ready', label: 'Ready to Publish', class: 'label-success' };
      } else {
        result = { status: 'draft', label: 'Draft', class: 'label-default' };
      }
    }
    
    that._statusCache.set(videoId, result);
    return result;
  };
  
  // Check if video is published
  this.isVideoPublished = function(video) {
    return video._deposit.status === 'published';
  };
  
  // Get video item CSS classes
  this.getVideoItemClasses = function(video) {
    var classes = [];
    
    if (that.isSelected(video._deposit.id)) {
      classes.push('active');
    }
    
    if (that.isLoading(video._deposit.id)) {
      classes.push('loading');
    }
    
    if (that.isVideoPublished(video)) {
      classes.push('video-published');
    } else {
      classes.push('video-editing');
    }
    
    return classes.join(' ');
  };
  
  // Get video title for display (cached)
  this.getVideoTitle = function(video) {
    var videoId = video._deposit.id;
    var cached = that._titleCache.get(videoId);
    if (cached) return cached;
    
    var result;
    if (video.title && video.title.title) {
      result = video.title.title;
    } else if (video._files && video._files.length > 0) {
      // Try to get title from the main video file
      var mainFile = video._files.find(f => f.context_type === 'master');
      if (mainFile) {
        result = mainFile.key || 'Untitled Video';
      } else {
        result = video._files[0].key || 'Untitled Video';
      }
    } else {
      result = 'Untitled Video';
    }
    
    that._titleCache.set(videoId, result);
    return result;
  };
  
  // Get video thumbnail or placeholder
  this.getVideoThumbnail = function(video) {
    // Try to find frame from files
    if (video._files) {
      var frameFile = video._files.find(f => f.key && f.key.includes('frame-'));
      if (frameFile && frameFile.links && frameFile.links.self) {
        return frameFile.links.self + '?width=120&height=68';
      }
    }
    
    // Return placeholder
    return '/static/img/video-placeholder.svg';
  };
  
  
  // Check if video is selected
  this.isSelected = function(videoId) {
    return that.selectedVideoId === videoId;
  };
  
  // Check if video is expanded
  this.isExpanded = function(videoId) {
    return that.expandedVideoId === videoId;
  };
  
  // Check if video is loading
  this.isLoading = function(videoId) {
    return that.loadingVideo === videoId;
  };
  
  // Get progress for processing videos
  this.getProcessingProgress = function(video) {
    if (!video._cds || !video._cds.state) return 0;
    
    var tasks = Object.keys(video._cds.state);
    var completedTasks = tasks.filter(task => 
      video._cds.state[task] === 'SUCCESS' || video._cds.state[task] === 'FAILURE'
    ).length;
    
    return Math.round((completedTasks / tasks.length) * 100);
  };
  
  // Get video description for display
  this.getVideoDescription = function(video) {
    // Try different possible paths for description
    if (video.description) {
      if (typeof video.description === 'string') {
        return video.description;
      } else if (video.description.description) {
        return video.description.description;
      }
    }
    
    // Try abstract field as fallback
    if (video.abstract) {
      if (typeof video.abstract === 'string') {
        return video.abstract;
      } else if (video.abstract.summary) {
        return video.abstract.summary;
      }
    }
    
    // Debug: log the video object structure (can be removed later)
    console.log('Video object for description debugging:', video);
    
    // Fallback message
    return 'No description available';
  };
  
  // Track expanded descriptions
  this.expandedDescriptions = new Set();
  
  // Toggle description expansion
  this.toggleDescription = function(videoId, event) {
    // Stop event from bubbling to prevent video selection
    if (event) {
      event.stopPropagation();
    }
    
    if (that.expandedDescriptions.has(videoId)) {
      that.expandedDescriptions.delete(videoId);
    } else {
      that.expandedDescriptions.add(videoId);
    }
  };
  
  // Check if description is expanded
  this.isDescriptionExpanded = function(videoId) {
    return that.expandedDescriptions.has(videoId);
  };
  
  // Filter videos based on status
  this.getFilteredVideos = function() {
    if (!that.videos) return [];
    
    switch (that.statusFilter) {
      case 'published':
        return that.videos.filter(function(video) {
          return that.isVideoPublished(video);
        });
      case 'draft':
        return that.videos.filter(function(video) {
          return !that.isVideoPublished(video);
        });
      default:
        return that.videos;
    }
  };
  
  // Set status filter
  this.setStatusFilter = function(filter) {
    that.statusFilter = filter;
    
    // If current selected video is not in filtered results, clear selection
    var filteredVideos = that.getFilteredVideos();
    var selectedVideoInFilter = filteredVideos.find(function(video) {
      return video._deposit.id === that.selectedVideoId;
    });
    
    if (!selectedVideoInFilter && filteredVideos.length > 0) {
      // Auto-select first video in filtered results
      that.selectedVideoId = filteredVideos[0]._deposit.id;
      $timeout(function() {
        that.expandedVideoId = filteredVideos[0]._deposit.id;
      }, 100);
    } else if (filteredVideos.length === 0) {
      // Clear selection if no videos match filter
      that.selectedVideoId = null;
      that.expandedVideoId = null;
    }
  };
  
  // Get filter counts
  this.getFilterCounts = function() {
    if (!that.videos) return { all: 0, published: 0, draft: 0 };
    
    var published = that.videos.filter(function(video) {
      return that.isVideoPublished(video);
    }).length;
    
    var draft = that.videos.length - published;
    
    return {
      all: that.videos.length,
      published: published,
      draft: draft
    };
  };
}

cdsVideoListCtrl.$inject = ['$scope', '$timeout'];

function cdsVideoList() {
  return {
    transclude: true,
    bindings: {
      videos: '=',
      maxNumberOfVideos: '<',
      isPublished: '&'
    },
    require: {
      cdsDepositsCtrl: '^cdsDeposits'
    },
    controller: cdsVideoListCtrl,
    template: `
      <div class="cds-video-list-sidebar">
        <!-- Header -->
        <div class="video-list-header mb-20" ng-if="$ctrl.videos.length > 0">
          <div class="row">
            <div class="col-md-12">
              <h4 class="mb-0">
                <i class="fa fa-video-camera"></i> 
                Videos
              </h4>
            </div>
          </div>
        </div>
        
        <!-- Side-by-side Video List View -->
        <div ng-if="$ctrl.videos.length > 0" class="video-sidebar-layout">
          <div class="row">
            <!-- Left sidebar with video list -->
            <div class="col-lg-4 col-md-5">
              <div class="video-sidebar">
                <!-- Status Filter in Sidebar -->
                <div class="video-sidebar-filter">
                  <div class="filter-header">
                    <small class="text-muted"><i class="fa fa-filter"></i> Filter by Status</small>
                  </div>
                  <div class="filter-buttons">
                    <div class="btn-group btn-group-sm" style="width: 100%;">
                      <button class="btn filter-btn" 
                              ng-class="{ 'btn-primary': $ctrl.statusFilter === 'all', 'btn-default': $ctrl.statusFilter !== 'all' }"
                              ng-click="$ctrl.setStatusFilter('all')">
                        <i class="fa fa-video-camera"></i> All
                        <span class="badge">{{ $ctrl.getFilterCounts().all }}</span>
                      </button>
                      <button class="btn filter-btn" 
                              ng-class="{ 'btn-warning': $ctrl.statusFilter === 'draft', 'btn-default': $ctrl.statusFilter !== 'draft' }"
                              ng-click="$ctrl.setStatusFilter('draft')">
                        <i class="fa fa-edit"></i> Draft
                        <span class="badge">{{ $ctrl.getFilterCounts().draft }}</span>
                      </button>
                      <button class="btn filter-btn" 
                              ng-class="{ 'btn-success': $ctrl.statusFilter === 'published', 'btn-default': $ctrl.statusFilter !== 'published' }"
                              ng-click="$ctrl.setStatusFilter('published')">
                        <i class="fa fa-check-circle"></i> Published
                        <span class="badge">{{ $ctrl.getFilterCounts().published }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                
                <div class="video-sidebar-header">
                  <small class="text-muted">Select a video to edit</small>
                </div>
                <div class="video-sidebar-list">
                  <div class="video-list-item" 
                       ng-repeat="video in $ctrl.getFilteredVideos() track by video._deposit.id"
                       ng-class="$ctrl.getVideoItemClasses(video)"
                       ng-click="$ctrl.selectVideo(video._deposit.id)">
                    <div class="video-item-content">
                      <div class="video-thumbnail-sidebar">
                        <img ng-src="{{ $ctrl.getVideoThumbnail(video) }}" 
                             alt="Video thumbnail">
                        <div ng-if="$ctrl.isLoading(video._deposit.id)" 
                             class="loading-overlay">
                          <i class="fa fa-spinner fa-spin"></i>
                        </div>
                      </div>
                      <div class="video-item-details">
                        <div class="video-header-row">
                          <div class="video-title-section">
                            <h6 class="video-title" title="{{ $ctrl.getVideoTitle(video) }}">
                              {{ $ctrl.getVideoTitle(video) }}
                            </h6>
                            <div class="video-meta">
                              <span class="video-number">Video #{{ $index + 1 }}</span>
                            </div>
                          </div>
                          <div class="video-actions">
                            <div ng-if="$ctrl.isVideoPublished(video)" class="video-status-published">
                              <span class="label label-success">
                                <i class="fa fa-check-circle"></i> Published
                              </span>
                              <a ng-href="/record/{{ video.recid }}" 
                                 target="_blank" 
                                 class="btn btn-xs btn-primary visit-video-btn"
                                 title="Visit video page">
                                <i class="fa fa-external-link"></i> View
                              </a>
                            </div>
                            <div ng-if="!$ctrl.isVideoPublished(video)" class="video-status-editing">
                              <span class="label {{ $ctrl.getVideoStatus(video).class }}">
                                <i class="fa fa-edit"></i> {{ $ctrl.getVideoStatus(video).label }}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div ng-if="$ctrl.getVideoStatus(video).status === 'processing'" 
                             class="video-progress-section">
                          <div class="progress progress-xs">
                            <div class="progress-bar progress-bar-info" 
                                 style="width: {{ $ctrl.getProcessingProgress(video) }}%">
                            </div>
                          </div>
                        </div>
                        <div class="video-description-section">
                          <div class="video-description" 
                               ng-class="{ 'expanded': $ctrl.isDescriptionExpanded(video._deposit.id) }">
                            <p class="description-text" 
                               ng-class="{ 'no-description': $ctrl.getVideoDescription(video) === 'No description available' }">
                              {{ $ctrl.getVideoDescription(video) }}
                            </p>
                            <div ng-if="$ctrl.getVideoDescription(video).length > 100 && $ctrl.getVideoDescription(video) !== 'No description available'" 
                                 class="description-toggle-text"
                                 ng-click="$ctrl.toggleDescription(video._deposit.id, $event)">
                              <span ng-if="!$ctrl.isDescriptionExpanded(video._deposit.id)" class="show-more">Show more</span>
                              <span ng-if="$ctrl.isDescriptionExpanded(video._deposit.id)" class="show-less">Show less</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Upload area in sidebar (using original style) -->  
                <div class="video-sidebar-upload" ng-if="$ctrl.cdsDepositsCtrl.master.metadata._deposit.status !== 'published' && $ctrl.videos.length < $ctrl.maxNumberOfVideos">
                  <div class="upload-divider"></div>
                  <div class="sidebar-upload-box cds-deposit-box"
                       ngf-drag-over-class="'cds-deposit-dragover'"
                       ngf-drop=""
                       ngf-change="$ctrl.cdsDepositsCtrl.addFiles($newFiles, $invalidFiles)"
                       ngf-select=""
                       ngf-accept="'.mp4,.mkv,.mov,.m4v'"
                       ngf-pattern="'.mp4,.mkv,.mov,.m4v'"
                       ngf-max-size="500GB"
                       ngf-multiple="true">
                    <div class="cds-deposit-box-upload-wrapper text-center">
                      <p class="cds-deposit-box-upload-icon">
                        <i class="fa fa-2x fa-video-camera" aria-hidden="true"></i>
                      </p>
                      <div class="cds-deposit-box-upload-content">
                        <div class="cds-deposit-box-upload-title">
                          <h5>Add more videos</h5>
                        </div>
                        <p class="cds-deposit-box-upload-description">Click or <strong>drag & drop</strong> files here</p>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Max videos message in sidebar -->
                <div class="video-sidebar-max-message" ng-if="$ctrl.videos.length >= $ctrl.maxNumberOfVideos">
                  <div class="upload-divider"></div>
                  <div class="max-videos-message">
                    <i class="fa fa-info-circle"></i>
                    <span>Maximum {{$ctrl.maxNumberOfVideos}} videos reached</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Right content area with video editor -->
            <div class="col-lg-8 col-md-7">
              <div class="video-editor-area">
                <div ng-if="!$ctrl.expandedVideoId" class="video-editor-placeholder">
                  <div class="text-center text-muted py-40">
                    <i class="fa fa-arrow-left fa-2x mb-20"></i>
                    <h4>Select a video to edit</h4>
                    <p>Choose a video from the list to view and edit its details</p>
                  </div>
                </div>
                
                <div ng-if="$ctrl.expandedVideoId">
                  <div ng-repeat="video in $ctrl.videos track by video._deposit.id" 
                       ng-if="video._deposit.id === $ctrl.expandedVideoId">
                    <div class="video-editor-content">
                      <div id="video_{{ video._deposit.id }}" class="video-details-container">
                        <cds-deposit
                          index="$index + 1"
                          id="video._deposit.id"
                          update-record-in-background="10000"
                          links="video.links"
                          schema="$ctrl.cdsDepositsCtrl.childrenSchemaResolved"
                          record="video"
                        >
                          <!-- Video header with actions inside cds-deposit scope -->
                          <div class="video-editor-header">
                            <div class="video-header-content">
                              <h4>
                                <i class="fa fa-video-camera"></i> 
                                {{ $ctrl.getVideoTitle(video) }}
                                <small class="text-muted">#{{ $index + 1 }}</small>
                              </h4>
                              <div class="video-header-actions">
                                <cds-actions template="/static/templates/cds_deposit/types/video/actions.html"></cds-actions>
                              </div>
                            </div>
                          </div>
                          <cds-form
                            template="/static/templates/cds_deposit/types/video/form.html"
                            form="$ctrl.cdsDepositsCtrl.childrenFormResolved"
                          >
                            <cds-uploader
                              auto-start-upload="true"
                              files="video._files"
                              template="/static/templates/cds_deposit/types/video/uploader.html"
                              remote-master-receiver="/api/flows/"
                            >
                            </cds-uploader>
                          </cds-form>
                        </cds-deposit>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        
        <!-- Empty state -->
        <div ng-if="$ctrl.videos.length === 0" class="text-center text-muted py-40">
          <i class="fa fa-video-camera fa-3x mb-20"></i>
          <h4>No videos yet</h4>
          <p>Upload video files to get started</p>
        </div>
        
        <!-- No videos match filter -->
        <div ng-if="$ctrl.videos.length > 0 && $ctrl.getFilteredVideos().length === 0" class="text-center text-muted py-40">
          <i class="fa fa-filter fa-2x mb-20"></i>
          <h4>No videos match the current filter</h4>
          <p>
            <span ng-if="$ctrl.statusFilter === 'published'">No published videos found.</span>
            <span ng-if="$ctrl.statusFilter === 'draft'">No draft videos found.</span>
          </p>
          <button class="btn btn-default btn-sm" ng-click="$ctrl.setStatusFilter('all')">
            <i class="fa fa-times"></i> Clear Filter
          </button>
        </div>
        
        <!-- Upload areas (shown in both views) -->
        <div ng-transclude></div>
      </div>
    `
  };
}

angular.module('cdsDeposit.components').component('cdsVideoList', cdsVideoList());