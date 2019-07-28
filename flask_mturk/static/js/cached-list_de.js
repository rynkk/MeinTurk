
var table = $('#cached_table').DataTable({
    "language": {
        "url": url_for_datatables_de
    },
    data: batches,
    "createdRow": function( row, data, dataIndex ) {
    },
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
        title: 'Löschung gespeicherter Batch!',
        content: 'Bist du dir sicher, dass du den Batch "<b>'+data.name+'</b>" löschen willst?<br>Dieser Vorgang lässt sich nicht umkehren und alle Umfragedaten gehen verloren!',
        buttons: {
            confirm:{
                btnClass: 'btn-red',
                action: function(){
                    $.alert({
                        title: 'Wirklich?',
                        content: 'Ganz sicher?',
                        buttons:{
                            yes:{
                                btnClass: 'btn-red',
                                action: async function () {
                                    const rawResponse = await fetch('/db/delete_cached/'+data.id, {
                                        method: 'DELETE'
                                    })
                                    const content = await rawResponse.json();
                                    if (content.success){
                                        table.row(row).remove()
                                        table.draw()
                                        show_alert("Erfolg", 'Gespeicherter Batch "'+data.name+'" wurde unwiderruflich gelöscht!', "success")
                                    }else{
                                        show_alert("Fehler", 'Irgendetwas ist schiefgelaufen: '+content.error, "danger")
                                    }
                                }
                            },
                            no:{
                                btnClass: 'btn-green'
                                // Do nothing
                            }
                        }
                    });
                }
                /**/
            },
            cancel: function () {
                // close
            }
        }
    });
});

    