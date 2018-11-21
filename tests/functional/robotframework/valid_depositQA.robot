*** Settings ***
Documentation     A test suite with tests for valid CDS Video deposit.
...
...               This test has a workflow that is created using keywords in
...               the imported resourceCDS file.
Resource          resourceCDS.robot

*** Variables
${SERVER}	cdslabs-qa.cern.ch
# ${SERVER}	videos.cern.ch


*** Test Cases ***
Valid Login
    Open Videos Main Page

    Main Page Should Be Open

    Login

When logged in deposit

# Upload local video file
    Open Deposit
    Open New Deposit
    Upload by URL 
    Confirm URL
    Fill project metadata
    Fill minimum video metadata

# Wait fully transcoded
#    Wait transcoding end

# Save project
#    Save all

# Publish project
#    Publish all

#    [Teardown]    Close Browser
