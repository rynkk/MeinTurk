
var table = $('#cached_table').DataTable({
    "language":{
        "url": datatables_translation
    },
    data: batches,
    "columns": [ 
        {
            "data": null,
            defaultContent: "",
            "searchable": false,
            "orderable": false,
        },
        { "data": "name" },
        { "data": "id"},
        { "data": "submitted"},
        { "data": "goal"},
        {
            "data": null,
            "searchable": false,
            "orderable": false,
            "render": function(data, type, row){                
                return "<a role='button' class='btn-primary btn btn-sm' href='/export_cached/"+row.id+"' download><i class='fas fa-download'></i></a>"
            },
        } ,
        {
            "data": null,
            "searchable": false,
            "orderable": false,
            "render": function(data, type, row){                
                return "<button type='button' class='btn-danger btn btn-sm delete-cached'><i class='fa fa-trash'></i></button>"
            },
        } ,
    ],
    "order": [[ 4, 'asc' ]]
});

table.on( 'order.dt search.dt', function () {
    table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
        cell.innerHTML = i+1+".";
    } );
}).draw();

$('#cached_table tbody').on('click', '.delete-cached', async function () {
    row = $(this).closest("tr")
    data = table.row(row).data()

    $.alert({
        title: _('Archived Batch Deletion!'),
        content: gt.strargs(_('Are you sure you want to delete the archived Batch "%1"?'), [data.name]) + '<br>' + _('This is non reversable and all data will be lost!'),
        buttons: {
            confirm:{
                text: _('confirm'),
                btnClass: 'btn-red',
                action: function(){
                    $.alert({
                        title: _('Really?'),
                        content: _('Are you sure?'),
                        buttons:{
                            yes:{
                                text: _('yes'),
                                btnClass: 'btn-red',
                                action: async function () {
                                    const rawResponse = await fetch('/db/delete_cached/'+data.id, {
                                        method: 'DELETE'
                                    })
                                    const content = await rawResponse.json();
                                    if (content.success){
                                        table.row(row).remove()
                                        table.draw()
                                        show_alert(_("Success"), gt.strargs(_('Successfully deleted archived Batch "%1"'), [data.name]), "success")
                                    }else{
                                        show_alert(_("Error"), _('Something went wrong: ')+content.error, "danger")
                                    }
                                }
                            },
                            no:{
                                text: _('no'),
                                btnClass: 'btn-green'
                                // Do nothing
                            }
                        }
                    });
                }
                /**/
            },
            cancel:{
                text: _('cancel'),
                // close
            }
        }
    });
});

    