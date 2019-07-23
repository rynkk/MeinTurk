
var table = $('#cached_table').DataTable({
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
        title: 'Cached-Batch Deletion!',
        content: 'Are you sure you want to delete the Batch "'+data.name+'"?<br>This is non reversable and all data will be lost!',
        buttons: {
            confirm:{
                btnClass: 'btn-red',
                action: function(){
                    $.alert({
                        title: 'Really?',
                        content: 'Are you sure?',
                        buttons:{
                            yes:{
                                btnClass: 'btn-red',
                                action: async function () {
                                    const rawResponse = await fetch('/api/delete_qualification_type/'+data.QualificationTypeId);
                                    const content = await rawResponse.json();
                                    table.row(row).remove()
                                    table.draw()
                                    show_alert("Success", 'Successfully deleted Qualification "'+data.Name+'" ('+data.QualificationTypeId+')', "success")
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

    