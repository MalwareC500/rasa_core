$(document).ready(function () {

    // add event listener on the login button

    $("#login").click(function () {

        facebookLogin();


    });

    // add event listener on the logout button

    $("#logout").click(function () {

        $("#logout").hide();
        $("#login").show();
        $("#status").empty();
        facebookLogout();

    });


    function facebookLogin() {
        FB.getLoginStatus(function (response) {
            console.log(response);
            statusChangeCallback(response, true);
        });
    }

    function statusChangeCallback(response, open_dialog) {
        if (response.status === "connected") {
            $("#login").hide();
            $("#logout").show();
            console.log(response);
            fetchUserProfile(response.authResponse.accessToken);
            subcribeApp();

        }
        else
            if (open_dialog === true) {
                // Logging the user to Facebook by a Dialog Window
                facebookLoginByDialog();
            }
    }

    function fetchUserProfile(access_token) {
        console.log('Welcome!  Fetching your information.... ');
        FB.api(`/oauth/access_token?grant_type=fb_exchange_token&client_id=2384158631685667&client_secret=bb66f42f8169ddc9adcb0e60bdfc9ba9&fb_exchange_token=${access_token}`, function (response) {
            console.log(response);
        });
        FB.api('/me?fields=id,name,email', function (response) {
            console.log(response);
            console.log('Successful login for: ' + response.name);
            var profile = `<h1>Welcome ${response.name}<h1>
         <h2>You can now use TalentBot within your pages.</h2>`;
            $("#status").append(profile);
        });
    }

    function subcribeApp() {
        console.log("subcribe app");
        FB.api('/me/accounts', function (response) {
            console.log(response);
            var pages = response.data;
            pages.forEach(page => {
                console.log(page.access_token);
                FB.api(`${page.id}/subscribed_apps?access_token=${page.access_token}`,
                    "POST",
                    {
                        "subscribed_fields": ["messages", "messaging_postbacks"]
                    },
                    function (response) {
                        console.log(response);
                        if (response.success == true) {
                            $.ajax({
                                url: "https://8b80a0b6.ngrok.io/webhooks/facebook/subscribe",
                                type: "POST",
                                contentType: "application/json",
                                data: { "page_id": page.id, "page_name": page.name, "page_access_token": page.access_token },
                                dataType: "json",
                                success: function (result) {
                                    console.log(result);
                                    // alert("Subscribed");
                                },
                                error: function (xhr, ajaxOptions, thrownError) {
                                    alert(xhr.status);
                                    alert(thrownError);
                                }
                            });
                        }
                    });
            });
        });
    }

    function unsubcribeAppAndLogout() {
        console.log("unsubcribe app");
        FB.api('/me/accounts', function (response) {
            console.log(response);
            var pages = response.data;
            pages.forEach(page => {
                console.log(page.access_token);
                FB.api(`${page.id}/subscribed_apps?access_token=${page.access_token}`,
                    "DELETE",
                    function (response) {
                        console.log(response);
                        if (response.success == true) {
                            $.ajax({
                                url: "https://8b80a0b6.ngrok.io/webhooks/facebook/subscribe",
                                type: "DELETE",
                                contentType: "application/json",
                                data: { "page_id": page.id },
                                dataType: "json",
                                success: function (result) {
                                    console.log(result);
                                    alert("You pages have unsubscribed to TalentBot. \nClick Continue with Facebook if you want to try TalentBot!");
                                },
                                error: function (xhr, ajaxOptions, thrownError) {
                                    alert(xhr.status);
                                    alert(thrownError);
                                }
                            });
                        }
                    });
            });

            FB.logout(function (response) {
                console.log(response);
                statusChangeCallback(response, false);
            });
        });
    }

    function facebookLoginByDialog() {
        FB.login(function (response) {

            statusChangeCallback(response, true);

        }, { scope: 'manage_pages,pages_show_list,public_profile,email,read_insights,pages_messaging,pages_messaging_phone_number' });
    }

    // logging out the user from Facebook

    function facebookLogout() {
        unsubcribeAppAndLogout();
    }


});