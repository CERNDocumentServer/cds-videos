*** Settings ***
Documentation	A resource file with reusable keywords and variables.
...
...               The system specific keywords created here form our own
...               domain specific language. They utilize keywords provided
...               by the imported Selenium2Library.
# Library           Selenium2Library
Library		Dialogs
Library		SeleniumLibrary	1	run_on_failure=Nothing
Library		String
Library		OperatingSystem
# Library           AngularJSLibrary

*** Variables ***
${SCRIPTDIR}	/afs/cern.ch/user/f/fcosta/private/QuickStartGuide/
${BROWSER}	Chrome
${DELAY}	0
${VALID USER}	demo
${VALID PASSWORD}	mode
${MY LOGIN}	flavio.costa@cern.ch
${MAIN PAGE}	http://${SERVER}
# ${LOGIN URL}	http://${SERVER}/login/?next=%2F
# ${LOGIN URL}	https://cdslabs-qa.cern.ch/oauth/login/cern/?next=%2Fdeposit%2Fnew%3Ftype%3Dproject
${LOGIN URL}	https://${SERVER}/oauth/login/cern/?next=%2Fdeposit%2Fnew%3Ftype%3Dproject
${OAUTH URL}	http://${SERVER}/oauth/login/cern/?next=%2F
${DEPOSIT URL}	http://${SERVER}/deposit
${NEW DEP URL}	http://${SERVER}/deposit/new?type=project
${FILE PATH}	/afs/cern.ch/project/cds/Testing/Masters/OPEN-MOVIE-2017-019-001.mov
${WELCOME URL}	http://${SERVER}/welcome.html
${ERROR URL}	http://${SERVER}/error.html
${TITLE}	Example 5
${DESCRIPTION}	${TITLE} description

*** Keywords ***
Open Videos Main Page
  Open Browser	${MAIN PAGE}	${BROWSER}
#  Maximize Browser Window
  Set Selenium Speed	${DELAY}
    
Main Page Should Be Open
#  Title Should Be	Home | CERN Document Server
  Title Should Be	CDS Videos · CERN

Login
  Go To		${LOGIN URL}
#    Click Element    Log in
#    Click Link       link="/login/?next=%2F"
#  Go TO		${OAUTH URL}
#  Sleep	1s
  Input Text	ctl00_ctl00_NICEMasterPageBodyContent_SiteContentPlaceholder_txtFormsLogin	${MY LOGIN}
#  Input Text	xpath://*[@id="ctl00_ctl00_NICEMasterPageBodyContent_SiteContentPlaceholder_txtFormsLogin"]	${MY LOGIN}

  ${key}=	Get File	${SCRIPTDIR}/DataFile.txt
  Input Password	//*[@id="ctl00_ctl00_NICEMasterPageBodyContent_SiteContentPlaceholder_txtFormsPassword"]	${key}
  Sleep	3
#  Click Element	xpath://*[@id="ctl00_ctl00_NICEMasterPageBodyContent_SiteContentPlaceholder_btnFormsLogin"]


############ >>> DEPOSIT STUFF #################
#    When logged in deposit

Open Deposit
#  Go To	${DEPOSIT URL}
  Sleep	3s
#  Click Element	xpath://*[@id="cds-navbar"]/ul/li[1]/a
  Click Link	Upload

Open New Deposit
#  Go To	${NEW DEP URL}
  Click Element	xpath://*[@id="cds-deposit-index"]/invenio-search/div/div/div[1]/div/div/div[3]/a

Upload local video file
  Click Element	xpath=//*[@class='fa fa-3x fa-cloud-upload']
    
  Pause Execution

Upload by URL 
#  Click Element	xpath://a[contains(.,'Upload by URL')]
  Sleep	3
  Click Button	xpath://*[@id="cds-deposit"]/cds-deposits/div[2]/div/div/div/div/div[2]/p[2]/button  
#  Input Text	xpath=//textarea[@placeholder="Input the URLs to upload here, i.e. https://example.com/video.mov, one per line"]    http://fcosta.web.cern.ch/fcosta/CERN-MOVIE-2017-023-001.mov
  Input Text	xpath=//textarea[@placeholder="Input the URLs to upload here, i.e. https://example.com/video.mov, one per line"]	http://fcosta.web.cern.ch/fcosta/test.mov

Confirm URL  
#  Click Element	xpath=//button[contains(.,'Upload URLs')]
  Sleep	3
  Click Element	xpath=//*[@id="cds-deposit"]/cds-deposits/div[2]/div/div/div/div/div[3]/cds-remote-uploader/div/div[1]/a

Fill project metadata

#  Input Text	name=title	${TITLE}
#  Select Frame	xpath=//div[@id='cke_1_contents']/iframe
#  Input Text	tag=body	${DESCRIPTION}
#  Unselect Frame
#  Current Frame Should Not Contain	${DESCRIPTION}obot valid_depositCDS.rob
#  Input Text	xpath=//div/input[@class[contains(.,'ui-select-search')]]	Accelerator
#  Press Key	xpath=//div/input[@class[contains(.,'ui-select-search')]]	\\13

##   CATEGORY
#    ${DD NG}        Get WebElement     xpath=//button[@data-placeholder='Category']
#    ${DD NG}        Get WebElement     xpath=//*[@id="$ctrl.master.metadata._deposit.id"]/div/div[2]/div/div/cds-form/div/div[2]/div[1]/div[2]/div[1]/div[1]/form/bootstrap-decorator/fieldset/div/button

#    Click Element   ${DD NG}
#  Sleep	3
  Wait Until Element Is Visible	xpath=//*[@id="$ctrl.master.metadata._deposit.id"]/div/div[2]/div/div/cds-form/div/div[2]/div[1]/div[2]/div[1]/div[1]/form/bootstrap-decorator/fieldset/div/button	3 
  Click Element	xpath=//*[@id="$ctrl.master.metadata._deposit.id"]/div/div[2]/div/div/cds-form/div/div[2]/div[1]/div[2]/div[1]/div[1]/form/bootstrap-decorator/fieldset/div/button
  ${DD ITEM NG}	Get WebElement	xpath=//a[@role='menuitem']/span[text()='CERN']
  Click Element	${DD ITEM NG}

##   TYPE
#    ${DD NG TYPE}        Get WebElement     xpath=//button[@data-placeholder='Type']
  Wait Until Element Is Visible	xpath://*[@id="$ctrl.master.metadata._deposit.id"]/div/div[2]/div/div/cds-form/div/div[2]/div[2]/div[2]/div[1]/div[2]/form/bootstrap-decorator/fieldset/div/button	3
  ${DD NG TYPE}	Get WebElement	xpath=//*[@id="$ctrl.master.metadata._deposit.id"]/div/div[2]/div/div/cds-form/div/div[2]/div[2]/div[2]/div[1]/div[2]/form/bootstrap-decorator/fieldset/div/button
  Click Element	${DD NG TYPE}
 
  ${DD ITEM NG}	Get WebElement	xpath=//a[@role='menuitem']/span[text()='VIDEO']
  Click Element	${DD ITEM NG}

##   NAME
#    ${DD SPAN NAME}        Get WebElement     xpath=//span[contains(@class,'btn btn-default form-control ui-select-toggle')]
#    Click Element   ${DD SPAN NAME}

#    ${DD NG NAME}        Get WebElement     xpath=//input[@placeholder='Author name']
##    Input Text      ${DD NG NAME}        Costa, Flavio:CERN
#    Input Text      ${DD NG NAME}        Costa Flavio
#    Wait until element contains      xpath=//div[@class='ui-select-choices-row ng-scope active']/a[@class='ui-select-choices-row-inner']/div[@class='ng-binding ng-scope']    Costa Flavio   
#    ${DD NG LIST ITEM}   Get WebElement     xpath=//*[@id="ui-select-choices-row-3-0"]/a/div/span

#    Wait Until Element Is Visible           ${DD NG LIST ITEM}       20
#    Click Element        ${DD NG LIST ITEM}

##   ROLE
#    ${DD NG ROLE}        Get WebElement     xpath=//select[@name='role']
#    Select From List      ${DD NG ROLE}      Narrator

Wait full upload

  Wait Until Page Contains	Video transcoding	3600

Fill minimum video metadata

  Reload Page

  Handle Alert
  
  Sleep	5
  
#	DESCRIPTION  

#  Input Text	xpath:/html	${DESCRIPTION}

  Select Frame	xpath=//div[@id='cke_2_contents']/iframe
  Input Text	tag=body	${DESCRIPTION}
  Unselect Frame


#  Wait Until Page Contains Element	css=iframe.cke_wysiwyg_frame	2s
#  Select Frame	css=iframe.cke_wysiwyg_frame
  

#	LANGUAGE

  ${DD ITEM LG}	Get WebElement	xpath=//select[@name="language"]
  
  Select From List By Label	${DD ITEM LG}	English   

#	DATE
  Click Element	xpath=//input[@name='date']
  Click Element	xpath=//button[contains(.,'14')]
  
#	Contributor Name

#  Wait Until Element Is Visible	xpath://*div[3]/cds-form/div[2]/div[2]/div/div[3]/div/div[1]/form/bootstrap-decorator[6]/div/div[1]/ul/li/sf-decorator/div/sf-decorator[2]/div/div[1]/div[1]/span	5s
#  Input Text	xpath://div[3]/cds-form/div[2]/div[2]/div/div[3]/div/div[1]/form/bootstrap-decorator[6]/div/div[1]/ul/li/sf-decorator/div/sf-decorator[2]/div/div[1]/div[1]/span	Costa Flavio:CERN

#  ${DD NG NAME}	Get WebElement	xpath=//*[@placeholder='Author name']
  ${DD NG NAME}	Get WebElement	xpath=//label[@class="control-label ng-binding field-required"]/span[@tabindex="-1"]
        
 
#  [@placeholder='Author name']
  Click Element	${DD NG NAME}
  
  <span tabindex="-1" class="btn btn-default form-control ui-select-toggle" aria-label="Select box activate" ng-disabled="$select.disabled" ng-click="$select.activate()" style="outline: 0;">
  <span ng-show="$select.isEmpty()" class="ui-select-placeholder text-muted ng-binding ng-hide">Author name</span> 
  <span ng-hide="$select.isEmpty()" class="ui-select-match-text pull-left" ng-class="{'ui-select-allow-clear': $select.allowClear &amp;&amp; !$select.isEmpty()}" ng-transclude="">
  <span class="ng-binding ng-scope">
        
  </span>
  </span> 
  <i class="caret pull-right" ng-click="$select.toggle($event)"></i> 
  <a ng-show="$select.allowClear &amp;&amp; !$select.isEmpty() &amp;&amp; ($select.disabled !== true)" aria-label="Select box clear" style="margin-right: 10px" ng-click="$select.clear($event)" class="btn btn-xs btn-link pull-right ng-hide">
  <i class="glyphicon glyphicon-remove" aria-hidden="true"></i>
  </a>
  </span>

  Input Text	${DD NG NAME}	Costa, Flavio:CERN 

#	Contributor Role

  ${DD NG ROLE}	Get WebElement	xpath=//select[@name='role']
  Select From List	${DD NG ROLE}	Narrator

#  Input text
#  //*div[3]/cds-form/div[2]/div[2]/div/div[3]/div/div[1]/form/bootstrap-decorator[6]/div/div[1]/ul/li/sf-decorator/div/sf-decorator[3]/div/select

Wait transcoding end
#    Sleep            300

  Wait Until Element Is Visible      //*[@id="child._deposit.id"]/div/div/div[2]/cds-form/div[3]/div/div[1]/div[2]/div[1]/div[5]/div/div/strong[contains(.,'Success')]      timeout=60m

    Wait Until Element Is Visible      //*[@id="toast-container"]/div/div[2]/div      timeout=60s


Save all
#   Wait for Save All (project) button
    Wait Until Element Is Visible      //*[@id="$ctrl.master.metadata._deposit.id"]/div/div[1]/div/div/div[2]/cds-actions/div/button[1]     timeout=300
#   Wait for Save (video) button
    Wait Until Element Is Visible      //*[@id="child._deposit.id"]/div/div/div[1]/span[2]/cds-actions/div[3]/button[2]     timeout=300
#   Click on Save All (project) button
    Click Button    //*[@id="$ctrl.master.metadata._deposit.id"]/div/div[1]/div/div/div[2]/cds-actions/div/button[1]

Publish all
    Wait Until Element Is Visible      //*[@id="$ctrl.master.metadata._deposit.id"]/div/div[1]/div/div/div[2]/cds-actions/div/button[2]       timeout=300
#    Sleep            120

    Click Button    //*[@id="$ctrl.master.metadata._deposit.id"]/div/div[1]/div/div/div[2]/cds-actions/div/button[contains(.,'Publish Project')]
#                    //*[@id="$ctrl.master.metadata._deposit.id"]/div/div[1]/div/div/div[2]/cds-actions/div/button[2]


############ DEPOSIT STUFF <<<<< #################

############ >>> DEPOSIT OBSOLETE ################
##   INEHERIT FROM PROJECT

#    Wait Until Element Is Visible            xpath=//div[@class='col-sm-12']/ul[@class='nav nav-tabs']/li[7]/a[@id='inherit-button']    300

#    Focus           xpath=//*[@id="inherit-button"]/i
    Focus           xpath=//div[@class='col-sm-12']/ul[@class='nav nav-tabs']/li[7]/a[@id='inherit-button']
    Click Element   xpath=//div[@class='col-sm-12']/ul[@class='nav nav-tabs']/li[7]/a[@id='inherit-button']

#   INHERIT ALL
    ${INHERIT ALL}        Get WebElement     xpath=//*[@id="child._deposit.id"]/div/div/div[2]/cds-form/div[3]/div/div[1]/div[2]/div[3]/div/ul/li[7]/ul/li[1]/a
    Click Element   ${INHERIT ALL}

#   ONLY MISSING FIELDS
    Click Element   xpath=//button[contains(.,'Only the missing fields')]


################ DEPOSIT OBSOLETE <<<< ###########

############ >>> SEARCH STUFF ####################

Enter ATLAS Search Query

  ${DD SEARCH}       Get WebElement     cds-navbar-form-input
#    Click Element    ${DD SEARCH}
  Input Text	${DD SEARCH}	ATLAS
  Press key	${DD SEARCH}	\\13

Check ATLAS Search Results
  Wait Until Element Is Visible	//*[@id="invenio-search"]/invenio-search/div/div/div/div/div[2]/div[1]/div/invenio-search-count/div[2]/ng-pluralize	timeout=300
  ${StringFromPage}	Get Text	//*[@id="invenio-search"]/invenio-search/div/div/div/div/div[2]/div[1]/div/invenio-search-count/div[2]/ng-pluralize
  ${NumRec}	Fetch From Right	${StringFromPage}	Found
  ${NumRec}	Fetch From Left	${NumRec}	results
  ${NumRec}=	Replace String	${NumRec}	'	${EMPTY}
  ${NumRec}=	Replace String	${NumRec}	,	${EMPTY}
  Should Be True	${NumRec} > 694	
  
  
############ SEARCH STUFF <<<<< ##################


# Open Browser To Login Page
#    Open Browser    ${LOGIN URL}    ${BROWSER}
#    Maximize Browser Window
#    Set Selenium Speed    ${DELAY}
#    Login Page Should Be Open

# Login Page Should Be Open
#    Title Should Be    Login Page

# Go To Login Page
#    Go To    ${LOGIN URL}
#    Login Page Should Be Open

# Input Username
#    [Arguments]    ${username}
#    Input Text    username_field    ${username}

# Input Password
#    [Arguments]    ${password}
#    Input Text    password_field    ${password}

# Submit Credentials
#    Click Button    login_button

# Welcome Page Should Be Open
#    Location Should Be    ${WELCOME URL}
#    Title Should Be    Welcome Page
