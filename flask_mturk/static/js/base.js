function getCookieValue(a) {
    var b = document.cookie.match('(^|;)\\s*' + a + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}

var language = getCookieValue('language')
if(language == "")
    $('.selectpicker').selectpicker('val', 'en')
else
    $('.selectpicker').selectpicker('val', language)

$('.selectpicker').on('change', function(){        
    var selected = $(this).val();
    document.cookie = 'language='+selected+'; max-age=31536000;'
    location.reload();
})

function toDate(dateString){
    return moment(dateString).calendar(null, {sameElse: 'LLL'})
}
