$.fn.dataTable.ext.type.order['date-pre'] = function ( data ) {
    var value = $(data).attr('val')
    if(isNaN(value)){
        return Number.MAX_SAFE_INTEGER
    }else{
        return parseInt(value)
    }
};

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
    "order": [[ 5, 'desc' ]]
});

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
$('#qualmodal').on('hidden.bs.modal', function(event){
    $("#qualmodal .modal-body input").val("").removeClass('error')
    $('#qualiderror').text('')
})

$('#qualmodal').on('show.bs.modal', function(event){
    var modal = $(this)
    var button = $(event.relatedTarget)
    var row = button.closest('tr[role="row"]')
    var data = table.row(row).data()
    modal.find(".modal-workerid").text(data.id)
    global_workerid = data.id
})

$('#assign-qual').on('click', async function(){
    // should use wtform validation etc but this will suffice
    var error = false
    var qualid = $('#qualid').val()
    var value = $('#qualvalue').val()
    if(value == ""){
        $('#qualvalue').addClass('error')
        error = true
    }
    if(qualid == ""){
        $('#qualid').addClass('error')
        error = true
    }
    if(!qualid.match(/^[A-Z0-9]*$/)){
        $('#qualid').addClass('error')
        $('#qualiderror').text(_('The QualificationID may only contain UpperCase-Letters and Digits'))
        error = true
    }
    if(!error){
        const rawResponse = await fetch("/api/assign_qualification/"+global_workerid+"/"+qualid+"/"+value, { method: 'PATCH' });
        const data = await rawResponse.json()
        if(data.success){
            show_alert(_('Success'), _('Successfully assigned the qualification!'), 'success')
        }else{
            show_alert(_('Error'), data.error, 'danger')
        }
    $('#qualmodal').modal('hide')
    // add csv export with selectable qualifications?
    }
})

