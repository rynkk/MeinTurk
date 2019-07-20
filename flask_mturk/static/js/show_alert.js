	function show_alert(heading, message, type){
            alert_class="alert-"+type

            $('#alert').addClass(alert_class)
            $('#alert .alert-heading').text(heading)
            $('#alert .alert-message').text(message)
            $('#alert').slideDown(function() {
                setTimeout(function() {
                    $('#alert').slideUp(function(){
                        $('#alert').removeClass(alert_class)
                        $('#alert .alert-heading').text("")
                        $('#alert .alert-message').text("")
                    });
                }, 5000);
            });
        }