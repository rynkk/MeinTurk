function getCookieValue(a) {
    var b = document.cookie.match('(^|;)\\s*' + a + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}

$('.selectpicker').selectpicker('val', getCookieValue('language'))

$('.selectpicker').on('change', function(){        
    var selected = $(this).val();
    document.cookie = 'language='+selected
    location.reload();
})