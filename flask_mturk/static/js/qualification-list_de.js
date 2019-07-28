var table = $('#qualification_table').DataTable({
    "language": {
        "url": url_for_datatables_de
    },
    data: quals,
    "createdRow": function( row, data, dataIndex ) {
        if (data.QualificationTypeStatus == "Active") {
            $(row).addClass( 'active' ) //TODO: work more with jquery data()
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
                return "<button type='button' class='btn-primary btn load-workers'>Laden</button>"
            },
        },
        { "data": "CreationTime"},
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
    "order": [[ 4, 'asc' ]]
});

table.on( 'order.dt search.dt', function () {
    table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
        cell.innerHTML = i+1+".";
    } );
}).draw();

$('#qualification_table tbody').on('click', '.load-workers', async function () {
    row = $(this).closest("tr")
    $(this).text("..........")
    data = table.row(row).data()
    const rawResponse = await fetch('/api/list_workers_with_qualification_type/'+data.QualificationTypeId);

    const content = await rawResponse.json();
    $(this).replaceWith(content.length)
} );

$('#qualification_table tbody').on('click', '.delete-qualification', async function () {
    row = $(this).closest("tr")
    data = table.row(row).data()

    $.alert({
        title: 'Qualifikationslöschung!',
        content: 'Willst du die Qualifikation "<b>'+data.Name+'</b>" sicher löschen? ',
        buttons: {
            bestätigen:{
                btnClass: 'btn-red',
                action: async function () {
                    const rawResponse = await fetch('/api/delete_qualification_type/'+data.QualificationTypeId, {
                        method: 'DELETE'
                        });
                    const content = await rawResponse.json();
                    table.row(row).remove()
                    table.draw()
                    show_alert("Erfolg", 'Qualifikation "'+data.Name+'" ('+data.QualificationTypeId+') erfolgreich gelöscht!', "success")
                }
            },
            abbrechen: function () {
                // close
            }
        }
    });
});


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
            form = $('#qualform')[0]        
            formData = new FormData(form);
    
            const rawResponse = await fetch('/qualifications', { 
                method: 'POST',
                body: formData
            })
            const json = await rawResponse.json()
            if (json.success){
                show_alert('Erfolg','Die Qualifikation wurde erstellt. Es könnte etwas dauern, bis AWS sie verarbeitet hat und sie in der Liste angezeigt wird.', 'success')
                $("#qualmodal").modal('hide');
            }else{
                show_alert('Fehler',json.error, 'danger')
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

/* DataTables language url is fetched asynchronously thus we need to wait until the table_length & table_filter exist*/
$(function(){
    $("#qualification_table_length").parent("div").removeClass("col-md-6").addClass("col-md-4")
    $("#qualification_table_filter").parent("div").removeClass("col-md-6").addClass("col-md-4")
    check_div = $("<div>").addClass("col-sm-12 col-md-4 column-centered")
        .append('<button type="button" class="btn btn-success" data-toggle="modal" data-target="#qualmodal"><i class="fas no-transform fa-plus-circle fa-lg"></i></button>')
    $("#qualification_table_length").parent("div").after(check_div)
})