    var timeout;

    function show_alert(heading, message, type){
            alert_class="alert-"+type+" alert"
            clearTimeout(timeout)
            $("#alert").hide()
            $("#alert").removeClass()

            $('#alert').addClass(alert_class)
            $('#alert .alert-heading').text(heading)
            $('#alert .alert-message').text(message)
            $('#alert').slideDown(function(){
                timeout = setTimeout(function(){
                    $('#alert').slideUp()
                },5000)
            })         
        }