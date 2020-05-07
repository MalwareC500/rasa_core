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
            // console.log(response);
            fetchUserProfile();
            subcribeApp(response.authResponse.accessToken, response.authResponse.userID);

        }
        else
            if (open_dialog === true) {
                // Logging the user to Facebook by a Dialog Window
                facebookLoginByDialog();
            }
    }

    function fetchUserProfile() {
        console.log('Welcome!  Fetching your information.... ');
        FB.api('/me?fields=id,name,email', function (response) {
            console.log(response);
            console.log('Successful login for: ' + response.name);
            var profile = `<h1>Welcome ${response.name}<h1>
         <h2>You can now use TalentBot within your pages.</h2>`;
            $("#status").append(profile);
        });
    }

    function subcribeApp(access_token, user_id) {
        console.log("subcribe app");
        FB.api(`/oauth/access_token?grant_type=fb_exchange_token&client_id=132626567238204&client_secret=e57ceca876f591c696d8e73edb5aa5fe&fb_exchange_token=${access_token}`, function (response) {
            console.log(response);
            var long_lived_access_token = response.access_token;
            FB.api(`/me/accounts?access_token=${long_lived_access_token}`, function (response) {
                console.log(response);
                var pages = response.data;
                pages.forEach(page => {
                    console.log(page.access_token);
                    FB.api(`/${page.id}/subscribed_apps?access_token=${page.access_token}`,
                        "POST",
                        {
                            "subscribed_fields": ["messages", "messaging_postbacks"]
                        },
                        function (response) {
                            console.log(response);
                            if (response.success == true) {
                                $.ajax({
                                    url: "https://ehiring-chatbot-5005.basecdn.net/webhooks/facebook/subscribe",
                                    type: "POST",
                                    contentType: "application/json",
                                    data: { "page_id": page.id, "page_name": page.name, "page_access_token": page.access_token, "page_admin_id": user_id },
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
                    FB.api(`/me/messenger_profile?access_token=${page.access_token}`,
                        "POST",
                        {
                            "get_started": {
                                "payload": "xin chào"
                            },
                            "persistent_menu": [
                                {
                                    "locale": "default",
                                    "composer_input_disabled": false,
                                    "call_to_actions": [
                                        {
                                            "type": "postback",
                                            "title": "Để lại lời nhắn",
                                            "payload": "để lại lời nhắn"
                                        },
                                        {
                                            "type": "postback",
                                            "title": "Thông tin tuyển dụng",
                                            "payload": "thông tin tuyển dụng"
                                        },
                                        {
                                            "type": "web_url",
                                            "title": "Về Base",
                                            "url": "https://base.vn/",
                                            "webview_height_ratio": "full"
                                        }
                                    ]
                                }
                            ]
                        },
                        function (response) {
                            console.log("set messenger profile: ", response);
                        }
                    );
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
                                url: "https://ehiring-chatbot-5005.basecdn.net/webhooks/facebook/subscribe",
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
                FB.api(`/me/messenger_profile?access_token=${page.access_token}`,
                    "DELETE",
                    {
                        "fields": [
                            "get_started",
                            "persistent_menu"
                        ]
                    },
                    function (response) {
                        console.log("del messenger profile: ", response);
                    }
                );
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

        }, { scope: 'manage_pages,pages_show_list,public_profile,email,pages_messaging,pages_messaging_phone_number' });
    }

    // logging out the user from Facebook

    function facebookLogout() {
        unsubcribeAppAndLogout();
    }


});