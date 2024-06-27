import angular from "angular";
import "angular-sanitize";
import "angular-lazy-image";
import "angular-local-storage";
import "angular-loading-bar";
import "angular-elastic";
import "bootstrap-sass";
import "ngmodal";
import "angular-sticky-plugin";
import "angular-scroll";

// Angular-Schema-Form
import "tv4";
import "angular-schema-form";
import "angular-schema-form-bootstrap";
import "angular-schema-form-dynamic-select";

// Autocomplete
import "angular-animate";
import "angular-strap";
import "angular-underscore";
import "ui-select";
import "angular-translate";

// UI sortable
import "angular-ui-sortable";

// CKEditor
import "ckeditor";
import "rr-ng-ckeditor/ng-ckeditor";
import "angular-schema-form-ckeditor/bootstrap-ckeditor";

// File uploader
import "ng-file-upload";
import "invenio-files-js/dist/invenio-files-js";

function cdsDepositsConfig(
  $locationProvider,
  depositExtractedMetadataProvider,
  depositStatesProvider,
  depositStatusesProvider,
  depositActions,
  inheritedPropertiesProvider,
  taskRepresentationsProvider,
  urlBuilderProvider,
  typeReducerProvider,
  localStorageServiceProvider,
  sfErrorMessageProvider,
  $httpProvider
) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });
  sfErrorMessageProvider.setDefaultMessage(0, "This field is required.");

  // Local storage configuration
  localStorageServiceProvider.setPrefix("cdsDeposit");

  var mainStatuses = [
    "file_upload",
    "file_download",
    "file_video_metadata_extraction",
    "file_video_extract_frames",
    "file_transcode",
  ];

  // Initialize the states
  depositStatesProvider.setValues(mainStatuses);

  // Initialize statuses provider
  depositStatusesProvider.setValues({
    PENDING: "PENDING",
    STARTED: "STARTED",
    FAILURE: "FAILURE",
    SUCCESS: "SUCCESS",
    CANCELLED: "CANCELLED",
  });

  // Initialize extracted metadata pre-fill
  depositExtractedMetadataProvider.setValues({
    values: {
      title: function (deposit, metadata) {
        if ("title" in metadata) {
          deposit.title = { title: metadata.title };
          return metadata.title;
        }
      },
      description: function (deposit, metadata) {
        if ("description" in metadata) {
          deposit.description = metadata.description;
          return metadata.description;
        }
      },
      keywords: function (deposit, metadata) {
        if ("keywords" in metadata) {
          deposit.keywords = metadata.keywords.map(function (keyword) {
            return { name: keyword, value: { name: keyword } };
          });
          return metadata.keywords.join(", ");
        }
      },
      date: function (deposit, metadata) {
        if ("creation_time" in metadata) {
          deposit.date = new Date(metadata.creation_time)
            .toISOString()
            .slice(0, 10);
          return deposit.date;
        }
      },
    },
  });

  // Deposit actions' information
  depositActions.setValues(["project", "video"]);

  inheritedPropertiesProvider.setValues([
    "contributors",
    "date",
    "description",
    "keywords",
    "license",
    "title.title",
    "translations",
  ]);

  taskRepresentationsProvider.setValues({
    file_upload: "Video file upload",
    file_download: "Video file download",
    file_transcode: "Video transcoding",
    file_video_extract_frames: "Video frame extraction",
    file_video_metadata_extraction: "Video metadata extraction",
  });

  // Initialize url builder
  urlBuilderProvider.setBlueprints({
    iiif: "/api/iiif/v2/<%=deposit%>:<%=version_id%>:<%=key%>/full/!<%=res%>/0/default.png",
    categories: "/api/categories",
    video: "/deposit/<%=deposit%>/preview/video/<%=key%>",
    restartTask: "/api/flows/<%=flowId%>/tasks/<%=taskId%>",
    restartFlow: "/api/flows/<%=flowId%>",
    taskFeedback: "/api/flows/<%=flowId%>/feedback",
    selfVideo: "/api/deposits/video/<%=deposit%>",
    bucketVideo: "/api/files/<%=bucket%>",
    actionVideo: "/api/deposits/video/<%=deposit%>/actions/<%=action%>",
    record: "/record/<%=recid%>",
  });

  // Initialize type reducer
  typeReducerProvider.setBlueprints({
    SUCCESS: function (type, data) {
      if (type === "update_deposit") {
        this.updateDeposit(data.meta.payload.deposit);
      }
    },
  });

  // // JWT Token
  // // Search DOM if exists
  // var authorized_token = document.getElementsByName("authorized_token");
  // if (authorized_token.length > 0) {
  //   var token = authorized_token[0].value;
  //   // No cache on API requests
  //   var headers = {
  //     Authorization: "Bearer " + token,
  //     "Content-Type": "application/json",
  //   };
  //   // Add no cache on all ``GET`` requests
  //   var _get = _.merge(headers, {
  //     "Cache-Control": "no-cache, no-store, must-revalidate",
  //     Pragma: "no-cache",
  //     Expires: 0,
  //   });
  //   $httpProvider.defaults.headers["delete"] = headers;
  //   $httpProvider.defaults.headers["post"] = headers;
  //   $httpProvider.defaults.headers["put"] = headers;
  // }

  // Optimize Angular on production
  // $compileProvider.debugInfoEnabled(false);
  var headers = {
    "Content-Type": "application/json",
  };
  $httpProvider.defaults.headers["delete"] = headers;
  $httpProvider.defaults.headers["post"] = headers;
  $httpProvider.defaults.headers["put"] = headers;
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = [
  "$locationProvider",
  "depositExtractedMetadataProvider",
  "depositStatesProvider",
  "depositStatusesProvider",
  "depositActionsProvider",
  "inheritedPropertiesProvider",
  "taskRepresentationsProvider",
  "urlBuilderProvider",
  "typeReducerProvider",
  "localStorageServiceProvider",
  "sfErrorMessageProvider",
  "$httpProvider",
  "$compileProvider",
];

// Register modules
angular.module("cdsDeposit.filters", []);
angular.module("cdsDeposit.providers", []);
angular.module("cdsDeposit.components", []);
angular.module("cdsDeposit.factories", []);

// Register all cdsDeposit module into one
angular
  .module("cdsDeposit.modules", [
    "cdsDeposit.filters",
    "cdsDeposit.providers",
    "cdsDeposit.factories",
    "cdsDeposit.components",
    "LocalStorageModule",
    "schemaForm",
  ])
  .config(cdsDepositsConfig);

angular
  .module("cdsDeposit.filters")
  .filter("taskRepr", function (taskRepresentations) {
    return function (input) {
      return taskRepresentations[input] || input;
    };
  });

angular.module("schemaForm").controller("invenioDynamicSelectController", [
  "$scope",
  "$controller",
  "$select",
  "$http",
  function ($scope, $controller, $select, $http) {
    $controller("dynamicSelectController", { $scope: $scope });

    // format return value for uiselectmultiple
    function formatTokenTags(item) {
      return {
        name: item,
        value: {
          name: item,
        },
      };
    }

    $scope.form.formatTokenTags = formatTokenTags;

    // Use this only in multiple select
    if ($scope.form.type === "uiselectmultiple") {
      // listen to keywords external change (inherit from project) and update the internal model
      $scope.$on("cds.deposit.form.keywords.inherit", function (event, record) {
        // format the keywords list for uiselectmultiple
        var value = record.keywords.map(function (item) {
          return formatTokenTags(item.name);
        });
        // assign it to the form internal model
        event.currentScope.internalModelTags = value;
      });
    }
  },
]);

// update the templateCache by preloading all the angular schema forms templates
angular.module("schemaForm").run([
  "$templateCache",
  function ($templateCache) {
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/array.html",
      '<div class="form-group schema-form-array clearfix {{form.htmlClass}}" sf-array="form" ng-model="$$value$$" ng-model-options="form.ngModelOptions"><label class="control-label" for="{{ form.key.slice(-1)[0] }}" ng-class="{\'sr-only\': !showTitle(), \'field-required\': form.required}" ng-show="showTitle()"><i ng-if="form.fa_cls" class="fa fa-fw {{ form.fa_cls }}"></i>&nbsp;{{ form.title }} </label><!-- with array sorting --><div ng-if="form.sortOptions"><ul class="list-unstyled" ng-model="modelArray" ui-sortable="evalExpr(form.sortOptions)" ><li class="{{ form.fieldHtmlClass }} list-group-item" ng-class="{\'deposit-inline\': form.inline, \'bg-warn\': form.firstItemMessage && $first}" ng-repeat="item in modelArray track by $index"><div ng-hide="(form.firstItemMessage && $first)" class="close-container pull-right" style="padding-bottom: 20px" ng-class="{\'clear-form\': !form.inline}"><i ng-hide="modelArray.length <= (form.options.minLength == null ? 1 : form.options.minLength)" class="sort-handle fa fa-sort fa-fw" ng-if="form.sortOptions.disabled === false"></i><button class="close" type="button" ng-hide="evalExpr(form.readonly) || form.remove === null || modelArray.length <= (form.options.minLength == null ? 1 : form.options.minLength) " ng-click="deleteFromArray($index)" ng-disabled="modelArray.length <= (form.options.minLength === null ? 1 : form.options.minLength)"><span aria-hidden="true">&times;</span></button></div><div class="pb-20" ng-if="form.firstItemMessage && $first"><span class="label label-default">{{form.firstItemMessage}}</span></div><div class="clearfix"></div><sf-decorator form="copyWithIndex($index)" ng-init="arrayIndex = $index"></sf-decorator></li></ul></div><!-- without array sorting (aka missing ``ui-sortable``)--><div ng-if="!form.sortOptions"><ul class="list-unstyled" ng-model="modelArray"><li class="{{ form.fieldHtmlClass }} list-group-item" ng-class="{\'deposit-inline\': form.inline, \'bg-warn\': form.firstItemMessage && $first}" ng-repeat="item in modelArray track by $index"><div ng-hide="(form.firstItemMessage && $first)" class="close-container pull-right" style="padding-bottom: 20px" ng-class="{\'clear-form\': !form.inline}"><i ng-hide="modelArray.length <= (form.options.minLength == null ? 1 : form.options.minLength)" class="sort-handle fa fa-sort fa-fw" ng-if="form.sortOptions.disabled === false"></i><button class="close" type="button" ng-hide="evalExpr(form.readonly) || form.remove === null || modelArray.length <= (form.options.minLength == null ? 1 : form.options.minLength) " ng-click="deleteFromArray($index)" ng-disabled="modelArray.length <= (form.options.minLength === null ? 1 : form.options.minLength)"><span aria-hidden="true">&times;</span></button></div><div class="pb-20" ng-if="form.firstItemMessage && $first"><span class="label label-default">{{form.firstItemMessage}}</span></div><div class="clearfix"></div><sf-decorator form="copyWithIndex($index)" ng-init="arrayIndex = $index"></sf-decorator></li></ul></div><div ng-model="modelArray"><div class="help-block" ng-show="(hasError() && errorMessage(schemaError())) || form.description" ng-bind-html="(hasError() && errorMessage(schemaError())) || form.description"></div><a class="add-button {{ form.style.add }}" ng-hide="evalExpr(form.readonly) || form.add === null" ng-click="appendToArray()" ng-disabled="form.schema.maxItems <= modelArray.length"><i class="fa fa-plus"></i>&nbsp;{{ form.add || \'Add\'}} </a></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/button.html",
      '<div class="form-group schema-form-submit {{ form.htmlClass }}"><div class="col-sm-9 col-sm-offset-3"><button class="btn {{ form.style || \'btn-default\' }}" type="button" ng-click="buttonClick($event,form)" ng-disabled="evalExpr(form.readonly)"><i ng-if="form.fa_cls" class="fa fa-fw {{ form.fa_cls }}"></i>&nbsp;{{ form.title }} </button></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/checkbox.html",
      '<div class="checkbox {{form.htmlClass}}" ng-class="{\'has-error\': form.disableErrorState !== true && hasError(), \'has-success\': form.disableSuccessState !== true && hasSuccess()}"><label class="{{form.labelHtmlClass}}"><input type="checkbox" ng-model="$$value$$" sf-changed="form" ng-disabled="evalExpr(form.readonly)" ng-model-options="form.ngModelOptions" schema-validate="form" class="{{form.fieldHtmlClass}}" name="{{form.key.slice(-1)[0]}}"><span ng-bind-html="form.title"></span></label><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/ckeditor.html",
      '<div class="form-group" ng-class="{\'has-error\': hasError()}"><label class="control-label" for="{{ form.key.slice(-1)[0] }}" ng-show="showTitle()" ng-class="{\'sr-only\': !showTitle(), \'field-required\': form.required}"><i ng-if="form.fa_cls" class="fa fa-fw {{ form.fa_cls }}"></i>{{form.title}} </label><textarea ng-show="form.key" style="background-color: white" type="text" class="form-control" schema-validate="form" ng-model="$$value$$" ng-disabled="evalExpr(form.readonly)" ckeditor="form.ckeditor"></textarea><span class="help-block">{{ (hasError() && errorMessage(schemaError())) || form.description}}</span></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/default.html",
      '<div class="form-group {{form.htmlClass}}" ng-class="{ \'{{\'schema-form-\' + form.type}}\': true, \'has-error\': form.disableErrorState !== true && hasError(), \'has-feedback\': form.feedback !== false }"><label class="{{ form.labelHtmlClass }}" for="{{ form.key.slice(-1)[0] }}" ng-if="!form.notitle" ng-class="{\'sr-only\': !showTitle(), \'field-required\': form.required}"><i ng-if="form.fa_cls" ng-class="\'fa fa-fw \' + form.fa_cls"></i>&nbsp;{{ form.title }} </label><input ng-if="!form.fieldAddonLeft && !form.fieldAddonRight" ng-show="form.key" type="{{ ::form.type }}" step="any" ng-model="$$value$$" sf-changed="form" placeholder="{{ ::form.placeholder }}" class="form-control {{ form.fieldHtmlClass }}" id="{{ form.key.slice(-1)[0] }}" ng-model-options="form.ngModelOptions" ng-disabled="evalExpr(form.readonly)" schema-validate="form" name="{{ form.key.slice(-1)[0] }}" aria-describedby="{{ form.key.slice(-1)[0] + \'Status\' }}"><div ng-if="form.fieldAddonLeft || form.fieldAddonRight" ng-class="{\'input-group\': (form.fieldAddonLeft || form.fieldAddonRight)}"><span ng-if="form.fieldAddonLeft" class="input-group-addon" ng-bind-html="form.fieldAddonLeft"></span><input ng-show="form.key" type="{{ form.type }}" step="any" ng-model="$$value$$" sf-changed="form" placeholder="{{ ::form.placeholder }}" class="form-control {{ form.fieldHtmlClass }}" id="{{ form.key.slice(-1)[0] }}" sf-field-model ng-disabled="evalExpr(form.readonly)" schema-validate="form" name="{{ form.key.slice(-1)[0] }}" aria-describedby="{{ form.key.slice(-1)[0] + \'Status\' }}"><span ng-if="form.fieldAddonRight" class="input-group-addon" ng-bind-html="form.fieldAddonRight"></span></div><span ng-if="form.feedback !== false" class="form-control-feedback" ng-class="evalInScope(form.feedback) || {\'glyphicon\': true, \'glyphicon-ok\': form.disableSuccessState !== true && hasSuccess(), \'glyphicon-remove\': form.disableErrorState !== true && hasError() }" aria-hidden="true"></span><span id="{{ form.key.slice(-1)[0] + \'Status\' }}" class="sr-only" ng-if="hasError() || hasSuccess()">{{ hasSuccess() ? \'(success)\' : \'(error)\' }}</span><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/fieldset.html",
      '<fieldset class="schema-form-fieldset {{ form.htmlClass }}" ng-disabled="evalExpr(form.readonly)" ng-init="collapsed = form.collapsed"><div class="panel panel-default deposit-panel"><div class="panel-heading" ng-click="collapsed = !collapsed"><a class="panel-toggle"> {{ form.title }} <span class="pull-right" ng-show="collapsed"><i class="glyphicon glyphicon-chevron-right"></i></span><span class="pull-right" ng-hide="collapsed"><i class="glyphicon glyphicon-chevron-down"></i></span></a></div><div class="panel-body" ng-hide="collapsed"><p ng-if="form.description" ng-bind-html="form.description"></p><sf-decorator ng-repeat="item in form.items" form="item"></sf-decorator></div></div></fieldset>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/radios_inline.html",
      '<div class="form-group schema-form-radios-inline {{ form.htmlClass }}" align="center" ng-class="{\'has-error\': form.disableErrorState !== true && hasError()}"><label class="control-label {{ form.labelHtmlClass }}" schema-validate="form" ng-model="$$value$$" ng-model-options="form.ngModelOptions" ng-class="{\'field-required\': form.required}" ng-show="showTitle()">{{ form.title }}</label><ul class="list-inline center-block"><li ng-repeat="item in form.titleMap"><label><i class="fa {{ item.fa_cls }} fa-2x fa-fw"></i><br/><span ng-bind-html="item.name"></span><br/><input class="{{ form.fieldHtmlClass }}" name="{{ form.key.join(\'.\') }}" type="radio" ng-model="$$value$$" sf-changed="form" ng-disabled="evalExpr(form.readonly)" ng-value="item.value"></label></li></ul><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/radios.html",
      '<div class="form-group schema-form-radios {{ form.htmlClass }}" ng-class="{\'has-error\': form.disableErrorState !== true && hasError()}"><label class="control-label {{ form.labelHtmlClass }}" ng-model="$$value$$" ng-model-options="form.ngModelOptions" schema-validate="form" ng-class="{\'field-required\': form.required}" ng-show="showTitle()">{{ form.title }}</label><div class="radio" ng-repeat="item in form.titleMap"><label><input type="radio" class="{{ form.fieldHtmlClass }}" sf-changed="form" ng-disabled="evalExpr(form.readonly)" ng-model="$$value$$" ng-value="item.value" name="{{ form.key.join(\'.\') }}"><span ng-if="item.fa_cls"><i ng-class="\'fa fa-fw \' + item.fa_cls"></i></span><span ng-bind-html="item.name"></span></label></div><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/select.html",
      '<div class="form-group {{form.htmlClass}} schema-form-select" ng-class="{\'has-error\': form.disableErrorState !== true && hasError(), \'has-feedback\': form.feedback !== false}"><label class="control-label {{form.labelHtmlClass}}" ng-show="showTitle()" ng-class="{\'field-required\': form.required}"><i ng-if="form.fa_cls" class="fa fa-fw {{ form.fa_cls }}"></i>{{form.title}} </label><select ng-model="$$value$$" ng-model-options="form.ngModelOptions" ng-disabled="evalExpr(form.readonly)" sf-changed="form" class="form-control {{ form.fieldHtmlClass }}" schema-validate="form" ng-options="item.value as item.name group by item.group for item in form.titleMap" name="{{ form.key.slice(-1)[0] }}"></select><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/strapselect.html",
      '<fieldset ng-controller="dynamicSelectController" class="form-group {{form.htmlClass}}" ng-disabled="evalExpr(form.readonly)" ng-class="{\'has-error\': hasError(), \'has-success\': hasSuccess()}"><label class="{{ form.labelHtmlClass }}" for="{{ form.key.slice(-1)[0] }}" ng-if="!form.notitle" ng-class="{\'sr-only\': !showTitle(), \'field-required\': form.required}"><i ng-if="form.fa_cls" ng-class="\'fa fa-fw \' + form.fa_cls"></i>&nbsp;{{ form.title }} </label><div class="form-group {{form.fieldHtmlClass}}" ng-init="populateTitleMap(form)"><button ng-if="(form.options.multiple == \'true\') || (form.options.multiple == true)" type="button" class="btn btn-default" ng-model="$$value$$" sf-changed="form" schema-validate="form" data-placeholder="{{form.placeholder || form.schema.placeholder || (\'placeholders.select\')}}" data-html="1" data-multiple="1" data-max-length="{{form.options.inlineMaxLength}}" data-placement="{{form.options.placement || \'bottom-left\'}}" data-max-length-html="{{form.options.inlineMaxLengthHtml}}" ng-disabled="form.disabled" bs-options="item.value as item.name for item in form.titleMap | selectFilter:this:$$value$$:&quot;$$value$$&quot;" bs-select></button><button ng-if="!((form.options.multiple == \'true\') || (form.options.multiple == true))" type="button" class="btn btn-default" ng-model="$$value$$" sf-changed="form" schema-validate="form" data-placeholder="{{form.placeholder || form.schema.placeholder || (\'placeholders.select\')}}" data-html="1" ng-disabled="form.disabled" data-placement="{{form.options.placement || \'bottom-left\'}}" bs-options="item.value as item.name for item in form.titleMap | selectFilter:this:$$value$$:&quot;$$value$$&quot;" bs-select></button><span class="help-block">{{ (hasError() && errorMessage(schemaError())) || form.description}} </span></div></fieldset>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/textarea.html",
      '<div class="form-group has-feedback {{ form.htmlClass }} schema-form-textarea" ng-class="{\'has-error\': form.disableErrorState !== true && hasError()}"><label class="control-label {{ form.labelHtmlClass }}" ng-class="{\'sr-only\': !showTitle(), \'field-required\': form.required}" for="{{ form.key.slice(-1)[0] }}"><i ng-if="form.fa_cls" class="fa fa-fw {{ form.fa_cls }}"></i> {{ form.title }} </label><textarea id="{{ form.key.slice(-1)[0] }}" class="form-control {{ form.fieldHtmlClass }}" name="{{ form.key.slice(-1)[0] }}" placeholder="{{ ::form.placeholder }}" ng-if="!form.fieldAddonLeft && !form.fieldAddonRight" ng-model="$$value$$" sf-changed="form" ng-disabled="evalExpr(form.readonly)" ng-model-options="form.ngModelOptions" schema-validate="form"></textarea><div ng-if="form.fieldAddonLeft || form.fieldAddonRight" ng-class="{\'input-group\': (form.fieldAddonLeft || form.fieldAddonRight)}"><span class="input-group-addon" ng-if="form.fieldAddonLeft" ng-bind-html="form.fieldAddonLeft"></span><textarea class="form-control {{ form.fieldHtmlClass }}" id="{{ form.key.slice(-1)[0] }}" ng-model="$$value$$" sf-changed="form" placeholder="{{ ::form.placeholder }}" ng-disabled="evalExpr(form.readonly)" ng-model-options="form.ngModelOptions" schema-validate="form" name="{{ form.key.slice(-1)[0] }}"></textarea><span ng-if="form.fieldAddonRight" class="input-group-addon" ng-bind-html="form.fieldAddonRight"></span></div><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/uiselectmultiple.html",
      '<div ng-init="internalModelTags=$$value$$" ng-controller="invenioDynamicSelectController" ng-class="{ \'has-error\': hasError(), \'has-feedback\': form.feedback !== false }" class="form-group"><label class="control-label" ng-show="showTitle()">{{form.title}}</label><ui-select ng-if="form.options.tagging == true" multiple tagging="form.formatTokenTags" tagging-tokens="SPACE|,|/" tagging-label="(custom \'new\')" ng-model="internalModelTags" sortable="form.options.sortable||false" theme="bootstrap" ng-disabled="evalExpr(form.readonly)" on-select="$$value$$.push($item)" on-remove="$$value$$.splice($$value$$.indexOf($item), 1)" class="{{form.options.uiClass}}"><ui-select-match placeholder="{{ form.placeholder || form.schema.placeholder || (\'placeholders.select\' | translate) }}"> {{$item.name}} </ui-select-match><ui-select-choices refresh="populateTitleMap(form, $select.search)" refresh-delay="form.options.refreshDelay" group-by="form.options.groupBy" repeat="item in form.titleMap | propsFilter: {name: $select.search}"><div ng-bind-html="item.name | highlight: $select.search"></div></ui-select-choices></ui-select><span ng-if="form.feedback !== false" ng-class="evalInScope(form.feedback) || { \'glyphicon\': true, \'glyphicon-ok\': hasSuccess(), \'glyphicon-remove\': hasError() }" class="form-control-feedback"></span><div class="help-block" sf-message="form.description"></div></div>'
    );
    $templateCache.put(
      "/static/templates/cds_deposit/angular-schema-form/uiselect.html",
      '<div class="form-group schema-form-uiselect {{form.htmlClass}}" ng-controller="invenioDynamicSelectController" ng-class="{\'has-error\': hasError(), \'has-feedback\': form.feedback !== false}" ng-init="insideModel=$$value$$; select_model.selected=$$value$$"><label class="control-label" for="{{ form.key.slice(-1)[0] }}" ng-class="{\'sr-only\': !showTitle(), \'field-required\': form.required}" ng-show="showTitle()"><i ng-if="form.fa_cls" class="fa fa-fw {{ form.fa_cls }}"></i>&nbsp;{{ form.title }} </label><ui-select ng-model="select_model.selected" ng-if="!(form.options.tagging||false)" ng-model-options="form.ngModelOptions" theme="bootstrap" ng-required="evalExpr(form.options.required || false)" ng-disabled="evalExpr(form.readonly)" on-select="$$value$$=$item.value; select_model.selected=$item" class="{{form.options.uiClass}}"><ui-select-match placeholder="{{ form.placeholder || form.schema.placeholder || (\'placeholders.select\' | translate)}}"> {{ $$value$$ | parseAutocomplete }} </ui-select-match><ui-select-choices minimum-input-length="{{ form.minLength || 3 }}" refresh="populateTitleMap(form, $select.search)" refresh-delay="form.options.refreshDelay" group-by="form.options.groupBy" repeat="item in form.titleMap"><div ng-bind-html="item.name | highlight: $select.search"></div><small ng-if="item.email"><{{item.email}}></small></ui-select-choices></ui-select><input type="hidden" name="{{form.key.slice(-1)[0]}}" ng-model="insideModel" sf-changed="form" ng-model-options="form.ngModelOptions" sf-field-model schema-validate="form"/><span id="{{form.key.slice(-1)[0] + \'Status\'}}" class="form-control-feedback" ng-if="form.feedback !== false" ng-class="evalInScope(form.feedback) || {\'glyphicon\': true, \'glyphicon-ok\': hasSuccess(), \'glyphicon-remove\': hasError() }"></span><div class="help-block" sf-message="form.description"></div></div>'
    );
  },
]);

// set angular-schema-forms custom templates
angular.module("schemaForm").config([
  "schemaFormDecoratorsProvider",
  function (decoratorsProvider) {
    const base = "/static/templates/cds_deposit/angular-schema-form/";
    const decorator = decoratorsProvider.decorator();
    decorator["array"].template = base + "array.html";
    decorator["button"].template = base + "button.html";
    decorator["checkbox"].template = base + "checkbox.html";
    decorator["ckeditor"].template = base + "ckeditor.html";
    decorator["default"].template = base + "default.html";
    decorator["fieldset"].template = base + "fieldset.html";
    decorator["radios-inline"].template = base + "radios_inline.html";
    decorator["radios"].template = base + "radios.html";
    decorator["select"].template = base + "select.html";
    decorator["strapselect"].template = base + "strapselect.html";
    decorator["textarea"].template = base + "textarea.html";
    decorator["uiselect"].template = base + "uiselect.html";
    decorator["uiselectmultiple"].template = base + "uiselectmultiple.html";
  },
]);

// Initialize the module
angular.module("cdsDeposit", [
  "cdsDeposit.modules",
  "ngCkeditor",
  "mgcrea.ngStrap",
  "mgcrea.ngStrap.modal",
  "pascalprecht.translate",
  "ui.sortable",
  "ui.select",
  "mgcrea.ngStrap.select",
  "mgcrea.ngStrap.datepicker",
  "mgcrea.ngStrap.helpers.dateParser",
  "mgcrea.ngStrap.tooltip",
  "ngFileUpload",
  "monospaced.elastic",
  "invenioFiles.filters",
  "afkl.lazyImage",
  "hl.sticky",
  "duScroll",
  "toaster",
  "angular-loading-bar",
  "schemaForm",
]);
