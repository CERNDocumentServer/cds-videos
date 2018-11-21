*** Settings ***
Documentation     A test suite with tests for valid CDS Video login.
...
...               This test has a workflow that is created using keywords in
...               the imported resourceCDS file.
Resource          resourceCDS.robot

*** Test Cases ***
Valid Login
    Open Videos Main Page
#    Input Username    demo
#    Input Password    mode
#    Submit Credentials
#    Welcome Page Should Be Open
# MainPage OK
    Main Page Should Be Open
# LoginURL
    Login


#    [Teardown]    Close Browser
