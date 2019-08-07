var ban_btn = "<button type='button' class='btn-sm btn-danger softblock'><i class='fas fa-lg fa-ban'></i></button>"
var unban_btn = "<button type='button' class='btn-sm btn-success softblock'><i class='fas fa-lg fa-thumbs-up'></i></button>"
var table = $('#worker_table').DataTable({
    "language":{
        "url": datatables_translation
    },
    data: workers,
    "columns": [ 
        {   
            "data": null,
            defaultContent: "a",
            "searchable": false,
            "orderable": false,
        },
        { "data": "id", "orderable": false },
        {
            "data": null,
            "render": function(data, type, row){                
                return row.no_app+'(+'+(row.no_ass-row.no_app-row.no_rej)+')'
            },
        },
        { "data": "no_rej" },
        { "data": "no_ass" },
        { "data": "last_submission" },
        {
            "data": null,
            "className":'softblock-td',
            "render": function(data, type, row){                
                return row.softblocked?_('Yes'):_('No')
            },
        },
        {
            "data": null,
            "searchable": false,
            "orderable": false,
            "render": function(data, type, row){
                if(row.softblocked)
                    return unban_btn
                else
                    return ban_btn
            },
        } ,
    ],
    "order": [[ 2, 'asc' ]]
});

table.on( 'order.dt search.dt', function () {
    table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
        cell.innerHTML = i+1+".";
    } );
}).draw();

$('#worker_table').on('click', '.softblock', async function(){
    $(this).prop('disabled', true)
    $(this).removeClass('btn-success btn-danger').addClass('btn-secondary')
    var parent = $(this).closest('tr')
    var softblock_td = parent.find('.softblock-td')
    var id = table.row(parent).data()['id']
    const rawResponse = await fetch('/db/toggle_softblock/'+id, {
        method: 'PATCH'
    });
    var content = await rawResponse.json()
    if(content.success){
        if(content.status){
            softblock_td.text(_('Yes'))
            $(this).replaceWith(unban_btn)
        }
        else{
            softblock_td.text(_('No'))
            $(this).replaceWith(ban_btn)
        }
        show_alert(_('Success'), gt.strargs(_('The worker with the ID "%1" was successfully'),[id]) +" "+ (content.status?_('softblocked'):_('unblocked')), 'success')
    }else
        show_alert(_('Error'), _('Something went wrong: ')+content.error, 'danger')
    $(this).prop('disabled', false)
})
