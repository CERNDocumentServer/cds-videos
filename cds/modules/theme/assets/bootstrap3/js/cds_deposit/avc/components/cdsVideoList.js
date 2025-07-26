import angular from "angular";
import _ from "lodash";

function cdsVideoListCtrl($scope, $timeout) {
  var that = this;
  
  // State management for video list
  this.selectedVideoId = null;
  this.expandedVideoId = null;
  this.videoListView = true; // Start in list view
  this.loadingVideo = null;
  
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
    // Auto-select and expand first video if available in list view
    if (that.videos && that.videos.length > 0 && that.videoListView) {
      that.selectedVideoId = that.videos[0]._deposit.id;
      // Auto-expand first video after a short delay
      $timeout(function() {
        that.expandedVideoId = that.videos[0]._deposit.id;
      }, 100);
    }
    
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
            
            // Auto-select the newest added video if in list view
            if (addedVideoIds.length > 0 && that.videoListView) {
              var newestVideoId = addedVideoIds[addedVideoIds.length - 1];
              that.selectedVideoId = newestVideoId;
              $timeout(function() {
                that.expandedVideoId = newestVideoId;
              }, 300);
            }
          }
        }
        
        // Auto-select first video when videos are loaded initially
        if (newVideos && newVideos.length > 0 && !that.selectedVideoId && that.videoListView) {
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
  
  // Toggle between list and detailed view
  this.toggleView = function() {
    that.videoListView = !that.videoListView;
    if (that.videoListView) {
      that.expandedVideoId = null;
    }
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
        <!-- Header with view toggle -->
        <div class="video-list-header mb-20" ng-if="$ctrl.videos.length > 0">
          <div class="row">
            <div class="col-md-8">
              <h4 class="mb-0">
                <i class="fa fa-video-camera"></i> 
                Videos ({{ $ctrl.videos.length }} of {{ $ctrl.maxNumberOfVideos }})
              </h4>
            </div>
            <div class="col-md-4 text-right">
              <div class="btn-group btn-group-sm">
                <button class="btn btn-default" 
                        ng-class="{ active: $ctrl.videoListView }"
                        ng-click="$ctrl.toggleView()"
                        title="List View">
                  <i class="fa fa-list"></i> List
                </button>
                <button class="btn btn-default" 
                        ng-class="{ active: !$ctrl.videoListView }"
                        ng-click="$ctrl.toggleView()"
                        title="Traditional View">
                  <i class="fa fa-th-large"></i> Full
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Side-by-side Video List View -->
        <div ng-if="$ctrl.videoListView && $ctrl.videos.length > 0" class="video-sidebar-layout">
          <div class="row">
            <!-- Left sidebar with video list -->
            <div class="col-lg-3 col-md-4">
              <div class="video-sidebar">
                <div class="video-sidebar-header">
                  <small class="text-muted">Select a video to edit</small>
                </div>
                <div class="video-sidebar-list">
                  <div class="video-list-item" 
                       ng-repeat="video in $ctrl.videos track by video._deposit.id"
                       ng-class="{ 
                         'active': $ctrl.isSelected(video._deposit.id),
                         'loading': $ctrl.isLoading(video._deposit.id)
                       }"
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
                        <div class="video-title-wrapper">
                          <h6 class="video-title" title="{{ $ctrl.getVideoTitle(video) }}">
                            {{ $ctrl.getVideoTitle(video) }}
                          </h6>
                          <div class="video-info-line">
                            <span class="video-number">Video #{{ $index + 1 }}</span>
                            <span ng-if="video.report_number" class="report-number">
                              {{ video.report_number[0] }}
                            </span>
                          </div>
                        </div>
                        <div class="video-status-section">
                          <div class="status-badge-wrapper">
                            <span class="label {{ $ctrl.getVideoStatus(video).class }}">
                              {{ $ctrl.getVideoStatus(video).label }}
                            </span>
                          </div>
                          <div ng-if="$ctrl.getVideoStatus(video).status === 'processing'" 
                               class="progress progress-xs">
                            <div class="progress-bar progress-bar-info" 
                                 style="width: {{ $ctrl.getProcessingProgress(video) }}%">
                            </div>
                          </div>
                        </div>
                        <div ng-if="video.keywords && video.keywords.length > 0" class="video-keywords-row">
                          <span ng-repeat="keyword in video.keywords | limitTo:5" class="label label-default keyword-pill">
                            {{ keyword.name }}
                          </span>
                          <span ng-if="video.keywords.length > 5" class="label label-info keyword-pill-more">
                            +{{ video.keywords.length - 5 }} more
                          </span>
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
            <div class="col-lg-9 col-md-8">
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
        
        <!-- Traditional Detailed View (when toggled) -->
        <div ng-if="!$ctrl.videoListView">
          <!-- Only show traditional video forms, not upload areas -->
          <div ng-repeat="child in $ctrl.videos track by child._deposit.id">
            <cds-deposit
              index="$index + 1"
              id="child._deposit.id"
              update-record-in-background="10000"
              links="child.links"
              schema="$ctrl.cdsDepositsCtrl.childrenSchemaResolved"
              record="child"
            >
              <div id="video_{{child._deposit.id}}" class="cds-deposit-panel panel panel-default">
                <div hl-sticky="" offset="0" container="video_{{child._deposit.id}}" class="panel-heading text-muted px-20 py-10">
                  <span class="text-muted">
                    <i class="fa fa-video-camera"></i> Video #{{$index + 1}} (of {{$ctrl.maxNumberOfVideos}}) <span ng-show="child.report_number" class="label ml-10 label-primary"> {{child.report_number[0]}} </span> <span ng-show="$ctrl.isPublished()" class="label ml-10 label-primary">Published</span>
                  </span>
                  <span class="pull-right">
                    <cds-actions template="/static/templates/cds_deposit/types/video/actions.html">
                    </cds-actions>
                  </span>
                </div>
                <div ng-init="showForm=false" class="panel-body">
                  <!-- Draft Video -->
                  <cds-form
                    template="/static/templates/cds_deposit/types/video/form.html"
                    form="$ctrl.cdsDepositsCtrl.childrenFormResolved"
                  >
                  <cds-uploader
                    auto-start-upload="true"
                    files="child._files"
                    template="/static/templates/cds_deposit/types/video/uploader.html"
                    remote-master-receiver="/api/flows/"
                  >
                    <!-- <cds-remote-uploader
                        template="/static/templates/cds_deposit/remote_upload.html"
                        remote-master-receiver="/api/flows/"
                        remote-children-receiver="/api/flows/"
                    > -->
                    </cds-remote-uploader>
                  </cds-uploader>
                  </cds-form>
                </div>
              </div>
            </cds-deposit>
          </div>
        </div>
        
        <!-- Empty state -->
        <div ng-if="$ctrl.videos.length === 0" class="text-center text-muted py-40">
          <i class="fa fa-video-camera fa-3x mb-20"></i>
          <h4>No videos yet</h4>
          <p>Upload video files to get started</p>
        </div>
        
        <!-- Upload areas (shown in both views) -->
        <div ng-transclude></div>
      </div>
    `
  };
}

angular.module('cdsDeposit.components').component('cdsVideoList', cdsVideoList());