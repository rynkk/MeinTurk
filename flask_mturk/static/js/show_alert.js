    var timeout;

    function show_alert(heading, message, type){
        var alert_class="alert-"+type+" alert"
            clearTimeout(timeout)
            $('.alertdiv').removeClass('z-5000')
            $("#alert").hide()
            $("#alert").removeClass()
            if($('body').hasClass('modal-open')){
                $('.alertdiv').addClass('z-5000')
            }
            $('#alert').addClass(alert_class)
            $('#alert .alert-heading').text(heading)
            $('#alert .alert-message').html(message)
            $('#alert').slideDown(function(){
                timeout = setTimeout(function(){
                    $('#alert').slideUp()
                },5000)
            })         
        }