$.fn.dataTable.ext.type.order['date-pre'] = function ( data ) {
    var value = $(data).attr('val')
    if(isNaN(value)){
        return Number.MAX_SAFE_INTEGER
    }else{
        return parseInt(value)
    }
};

var table = $('#qualification_table').DataTable({
    "language":{
        "url": datatables_translation
    },
    data: quals,
    "createdRow": function( row, data, dataIndex ) {
        if (data.QualificationTypeStatus == "Active") {
            $(row).addClass( 'active' )
        }else{
            $(row).addClass( 'inactive' )
        }
    },
    "columns": [ 
        {   "data": null,
            defaultContent: "",
            "searchable": false,
            "orderable": false,
        },
        { "data": "Name" },
        { "data": "QualificationTypeId", "orderable": false },
        {
            "orderable": false,
            "searchable": false,
            "render": function(data, type, row){
                return "<button type='button' class='btn-primary btn load-workers'>"+_("Load")+"</button>"
            },
        },
        {
            "data": null,
            "render": function(data, type, row){
                return "<span val="+new Date(data.CreationTime).getTime()+">"+toDate(data.CreationTime)+"</span>" //necessary hack for DataTables sorting :(
            },
            "type": "date"
        },
        { "data": "Description", "orderable": false  },
        {
            "data": null,
            "searchable": false,
            "orderable": false,
            "render": function(data, type, row){                
                return "<button type='button' class='btn-sm btn-danger delete-qualification'><i class='fa fa-trash'></i></button>"
            },
        } ,
    ],
    "order": [[ 4, 'desc' ]],
    "initComplete": function( settings, json ) {
        configure_header()
    }
});

table.on( 'order.dt search.dt', function () {
    table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
        cell.innerHTML = i+1+".";
    } );
}).draw();

$('#qualification_table tbody').on('click', '.load-workers', async function () {
    var row = $(this).closest("tr")
    $(this).text("..........")
    var data = table.row(row).data()
    const rawResponse = await fetch('/api/list_workers_with_qualification_type/'+data.QualificationTypeId);

    const content = await rawResponse.json();
    $(this).replaceWith(content.length)
} );

$('#qualification_table tbody').on('click', '.delete-qualification', async function () {
    var row = $(this).closest("tr")
    var data = table.row(row).data()

    $.alert({
        title: _('Qualification Deletion!'),
        content: gt.strargs(_('Are you sure you want to delete the Qualification "%1"?'), [data.Name]),
        buttons: {
            confirm:{
                text: _('confirm'),
                btnClass: 'btn-red',
                action: async function () {
                    const rawResponse = await fetch('/api/delete_qualification_type/'+data.QualificationTypeId, {
                        method: 'DELETE'
                        });
                    const content = await rawResponse.json();
                    table.row(row).remove()
                    table.draw()
                    show_alert(_("Success"), gt.strargs(_('Successfully deleted Qualification "%1" (%2)'), [data.Name, data.QualificationTypeId]), "success")
                }
            },
            cancel:{
                text: _('cancel'),
            }
        }
    });
});

function configure_header(){
    $("#qualification_table_length").parent("div").removeClass("col-md-6").addClass("col-md-3")
    $("#qualification_table_filter").parent("div").removeClass("col-md-6").addClass("col-md-3")
    var header_div = $("<div>").addClass("col-sm-12 col-md-6 column-centered")
        .append('<button type="button" class="btn btn-success mr-5" data-toggle="modal" data-target="#qualmodal"><i class="fas no-transform fa-plus-circle fa-lg"></i></button>')
        .append('<div class="form-check form-check-inline ml-5">'+
                    '<label for="hide_batched" class="form-check-label">'+_('Hide Batch qualifications')+'</label>'+
                    '<input id="hide_batched" type="checkbox" class="form-check-input" style="margin-left:1rem">'+
                '</div>')
    $("#qualification_table_length").parent("div").after(header_div)
    
        $("#hide_batched").on("click",function() {
            if($(this).prop("checked")){
                $.fn.dataTable.ext.search.push(
                function (settings, data, dataIndex) {
                    var row_data = table.row(dataIndex).data()
                    if(row_data.Description.includes('MiniBatch-Qual'))
                        return false
                    else
                        return true
                    }
                );
            }else{
                $.fn.dataTable.ext.search.pop();
            }               
            table.draw();
        });
}

$("#qualform input").blur(function() {
    $(this.form).validate().element(this);
});

$('#qualmodal').on('show.bs.modal',function(event){
    $('#qualform')[0].reset();
    $('div.bootstrap-tagsinput').tagsinput('removeAll');
});

$("#qualform").validate({
    ignore: "",
    submitHandler: function(form){
        (async () => {
            var form = $('#qualform')[0]        
            var formData = new FormData(form);
    
            const rawResponse = await fetch('/qualifications', { 
                method: 'POST',
                body: formData
            })
            const json = await rawResponse.json()
            if (json.success){
                show_alert(_('Success'), _('The qualification was successfully created. It might take some time until AWS processed it and it shows up.'), 'success')
                $("#qualmodal").modal('hide');
            }else{
                show_alert(_('Error'),json.error, 'danger')
            }
          })(); 
    }
});

$('#create_qual').on("click", function(){
    $('#qualform').submit()
})

$('#auto_granted_value').closest('.row').css('visibility', 'hidden')

$("#auto_granted").on("change", function(){
    if(this.checked){
        $('#auto_granted_value').closest('.row').css('visibility', 'visible')
    }else{        
        $('#auto_granted_value').closest('.row').css('visibility', 'hidden')
    }
    
})
