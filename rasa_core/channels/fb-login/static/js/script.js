$(document).ready(function(){   
 
    // add event listener on the login button
    
    $("#login").click(function(){
   
       facebookLogin();
   
      
    });
   
    // add event listener on the logout button
   
    $("#logout").click(function(){
   
      $("#logout").hide();
      $("#login").show();
      $("#status").empty();
      facebookLogout();
   
    });
   
   
    function facebookLogin()
    {
      FB.getLoginStatus(function(response) {
          console.log(response);
          statusChangeCallback(response);
      });
    }
   
    function statusChangeCallback(response)
    {
        console.log(response);
        if(response.status === "connected")
        {
           $("#login").hide();
           $("#logout").show(); 
           fetchUserProfile();
           subcribeApp();

        }
        else{
            // Logging the user to Facebook by a Dialog Window
            facebookLoginByDialog();
        }
    }
   
    function fetchUserProfile()
    {
      console.log('Welcome!  Fetching your information.... ');
      FB.api('/me?fields=id,name,email', function(response) {
        console.log(response);
        console.log('Successful login for: ' + response.name);
        var profile = `<h1>Welcome ${response.name}<h1>
         <h2>Your email is ${response.email}</h2>`;
        $("#status").append(profile);
      });
    }

    function subcribeApp() {
        console.log("subcribe app");
        FB.api('/me/accounts', function(response) {
            console.log(response);
            var pages = response.data;
            pages.forEach(page => {
                console.log(page.access_token);
                FB.api(`${page.id}/subscribed_apps?access_token=${page.access_token}`,
                        "POST",
                        {
                            "subscribed_fields": ["messages", "messaging_postbacks"]
                        },
                        function(response) {
                            console.log(response);
                            if (response.success == true) {
                                $.ajax({
                                    url: "https://310140f7.ngrok.io/subscribe",
                                    type: "POST",
                                    contentType: "application/x-www-form-urlencoded",
                                    data: { "page_id": page.id, "page_name": page.name, "page_access_token": page.access_token },
                                    dataType: "json",
                                    success: function (result) {
                                        console.log(result);
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
   
    function facebookLoginByDialog()
    {
      FB.login(function(response) {
         
          statusChangeCallback(response);
         
      }, {scope: 'manage_pages,pages_show_list,public_profile,email,read_insights,pages_messaging,pages_messaging_phone_number'});
    }
   
    // logging out the user from Facebook
   
    function facebookLogout()
    {
      FB.logout(function(response) {
          statusChangeCallback(response);
      });
    }
   
   
   });