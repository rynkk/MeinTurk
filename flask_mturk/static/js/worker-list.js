$.fn.dataTable.ext.type.order['date-pre'] = function ( data ) {
    var value = $(data).attr('val')
    if(isNaN(value)){
        return Number.MAX_SAFE_INTEGER
    }else{
        return parseInt(value)
    }
};

var ban_btn = "<button type='button' class='btn-sm btn-danger softblock' data-toggle='tooltip' title='Softblock'><i class='fas fa-lg fa-ban'></i></button>"
var unban_btn = "<button type='button' class='btn-sm btn-success softblock' data-toggle='tooltip' title='Unblock'><i class='fas fa-lg fa-thumbs-up'></i></button>"
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
                return row.no_app + (row.no_ass-row.no_app-row.no_rej==0?'':'(+'+(row.no_ass-row.no_app-row.no_rej)+')')
            },
        },
        { "data": "no_rej" },
        { "data": "no_ass" },
        {
            "data": null,
            "render": function(data, type, row){
                return "<span val="+new Date(row.last_submission).getTime()+">"+toDate(row.last_submission)+"</span>" //necessary hack for DataTables sorting :(
            }
        },
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
                return "<button type='button' class='btn-sm btn-success' data-toggle='modal' data-target='#qualmodal'><i class='fas fa-plus-circle'></i></button>"
            },
        } ,
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
    "order": [[ 5, 'desc' ]],
    "initComplete": function( settings, json ) {
        $("#worker_table_length").parent("div").removeClass("col-md-6").addClass("col-md-4")
        $("#worker_table_filter").parent("div").removeClass("col-md-6").addClass("col-md-4")
        var check_div = $("<div>").addClass("col-md-4")
            .append('<button type="button" class="btn btn-primary" data-toggle="modal" data-target="#csvmodal">'+_('CSV-Actions')+'</button>')
        $("#worker_table_length").parent("div").after(check_div)
        $('button[data-toggle="tooltip"]').tooltip()
    }
});

$('#multiselect').selectpicker()

table.on( 'order.dt search.dt', function () {
    table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
        cell.innerHTML = i+1+".";
    } );
}).draw();

$.fn.dataTable.ext.type.order['date-pre'] = function ( data ) {
    var value = $(data).attr('val')
    if(isNaN(value)){
        return Number.MAX_SAFE_INTEGER
    }else{
        return parseInt(value)
    }
};

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
            $(this).tooltip('hide')
            $(this).replaceWith(unban_btn)
        }
        else{
            softblock_td.text(_('No'))
            $(this).tooltip('hide')
            $(this).replaceWith(ban_btn)
        }
        $('button[data-toggle="tooltip"]').tooltip()
        show_alert(_('Success'), gt.strargs(_('The worker with the ID "%1" was successfully'),[id]) +" "+ (content.status?_('softblocked'):_('unblocked')), 'success')
    }else
        show_alert(_('Error'), _('Something went wrong: ')+content.error, 'danger')
    $(this).prop('disabled', false)
})
$('#qualmodal').on('hidden.bs.modal', function(event){
    $("#qualmodal .modal-body input").val(1).removeClass('error')
    $('#qualmodal label.error').text('')
})

$('#qualmodal').on('show.bs.modal', function(event){
    var modal = $(this)
    var button = $(event.relatedTarget)
    var row = button.closest('tr[role="row"]')
    var data = table.row(row).data()
    modal.find(".modal-workerid").text(data.id)
    global_workerid = data.id
})

function isPositiveInteger(s) {
    return /^\+?[0-9][\d]*$/.test(s);
}

$('#assign-qual').on('click', async function(){
    var value = $('#value').removeClass('error')
    $('#invalid_qualval').text('')
    var qualid = $('#select').val()
    var value = $('#value').val()
    if(!(isPositiveInteger(value))){
        var value = $('#value').addClass('error')
        $('#invalid_qualval').text('Please enter an Integer geq 0.')
        return
    }
    const rawResponse = await fetch("/api/assign_qualification/"+global_workerid+"/"+qualid+"/"+value, { method: 'PATCH' });
    const data = await rawResponse.json()
    if(data.success){
        show_alert(_('Success'), _('Successfully assigned the qualification!'), 'success')
    }else{
        show_alert(_('Error'), data.error, 'danger')
    }
})

$('#exportcsv').on('click', async function(){
    $('button[data-id="multiselect"]').removeClass('error')
    $("#fileerror").text('')
    if($('#multiselect').val().length == 0){
        $('button[data-id="multiselect"]').addClass('error')
        $("#fileerror").text(_('This field is required.'))
        return
    }
    var form = $('#downloadform')[0]
    var formData = new FormData(form);

    const rawResponse = await fetch('/export_workers', { 
        method: 'POST',
        body: formData
    })
    if(rawResponse.status == 200){
        const data = await rawResponse.blob()
        download(data, "worker_export.csv", "text/csv");
        show_alert(_('Success'),_('Successfully downloaded the CSV.'), 'success')
    }else if(rawResponse.status == 500){
        const data = await rawResponse.text()
        show_alert(_('Internal Server Error'),_('Something went terribly wrong: ') + data, 'danger')
    }else{       
        const data = await rawResponse.json()
        show_alert(_('Error'), data.error, 'danger')
    }
})

$('#csvmodal').on('hidden.bs.modal', function(event){
    var modal = $(this)
    $("#uploadform #file").val('').removeClass("error")
    $("#multiselect").val('').selectpicker("refresh");
    modal.find("button.error").removeClass('error')
    modal.find("label.error, div.error").empty()
})

$("#uploadcsv").on("click", async function(){
    $("#uploadform label.error").empty()
    $("#uploadform div.error").empty()
    $("#uploadform div.success").empty()
    $("#uploadform #file").removeClass("error")
    if(!$("#uploadform #file").val()){
        $("#uploadform label.error").append(_("This field is required."))
        $("#uploadform #file").addClass("error")
        return
    }

    var form = $('#uploadform')[0]
    var formData = new FormData(form);

    $('body').addClass("loading")

    const rawResponse = await fetch('/upload_workers', { 
        method: 'POST',
        body: formData
        })
    $('body').removeClass("loading")
    if (rawResponse.status == 500){
        const text = await rawResponse.text()
        show_alert(_('Internal Server Error'), _('Something went wrong:')+text, 'danger')
        return;
    }
    const json = await rawResponse.json()
    if(json.success){     
        
        // Adding warnings if any
        // Why do Dicts in JS not have an inbuilt method to check if empty, or atleast a length?
        if(Object.keys(json.warnings).length > 0){
            show_alert(_('Some Success'), _('Successfully completed the request, but there were some errors caught!'), 'warning')   
            $("#uploadform div.error").append('<h4>'+_('Warnings')+':<h4>')
            for(let i in json.warnings){
                var li = $('<li>').text(_("Row ")+i)
                var ul = $('<ul>')
                for(let j in json.warnings[i]){
                    var row_li = $('<li>').text(json.warnings[i][j])
                    ul.append(row_li)
                }
                $("#uploadform div.error").append($('<ul>').append(li.append(ul)))                                
            }
        }else{            
            show_alert(_('Success'), _('Successfully assigned the specified qualifications'), 'success')   
        }
    }else{
        $("#uploadform label.error").empty()
        $("#uploadform div.error").empty()
        $("#uploadform #file").addClass("error")
        if(json.errortype == 'main'){
            $("#uploadform div.error").append('<h4>'+json.errors.main+'</h4>')
        }else if(json.errortype == 'document'){
            $("#uploadform div.error").append('<h4>'+_('Logic-error in CSV')+'<h4>')
            for(let i in json.errors){
                var li = $('<li>').text(_("Row ")+i)
                var ul = $('<ul>')
                for(let j in json.errors[i]){
                    var row_li = $('<li>').text(json.errors[i][j])
                    ul.append(row_li)
                }
                $("#uploadform div.error").append($('<ul>').append(li.append(ul)))
                
            }
        }else if(json.errortype == 'form'){
            for(let i in json.errors)
                $("#uploadform label.error").append(json.errors[i]+'<br/>')
        }
    }
})        