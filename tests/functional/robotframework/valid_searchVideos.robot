*** Settings ***
Documentation     A test suite with tests for valid CDS Video Search.
...
...               This test has a workflow that is created using keywords in
...               the imported resourceCDS file.
Resource          resourceCDS.robot

*** Variables
${SERVER}	videos.cern.ch

*** Test Cases ***

Valid Login
    Open Videos Main Page
    Main Page Should Be Open

#    Login

First Search Case: ATLAS
    Enter ATLAS Search Query    
    Check ATLAS Search Results


# When logged in deposit
#    Open Deposit
#    Open New Deposit
#    Wait for Angular
#    Upload local video file
#    Fill project metadata


#    [Teardown]    Close Browser
