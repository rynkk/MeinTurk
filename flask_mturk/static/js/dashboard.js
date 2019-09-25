var render_surveys=[]

for(let hit_index in surveys){ // Add HITs that are not to be batched
    var hit = surveys[hit_index]
    if(hit.hasOwnProperty('RequesterAnnotation') && hit['RequesterAnnotation'].includes('batch'))
        continue
    hit.batched = false

    for(let i in hidden_hits){
        if (hidden_hits[i][0]==hit.HITId)
            hit.hidden=true
    }
    render_surveys.push(hit)
}

//TODO CHANGE THIS 
ordering.forEach((item) => { //TODO change, maybe add group parameter to ordering
    var minihits = get_elements_with_value(surveys, "RequesterAnnotation", "batch"+item.batch_id)
    var hits_order = item.hits
    for(let i=0; i<minihits.length; i++){
        var hit = minihits[i] 
        if(hit.hasOwnProperty("HITId")){ //if hit is not queued it has an ID
            var hit_order = get_element_with_value(hits_order, "id", hit.HITId)
            if(hit_order){
                hit.position = hit_order.position
                hit.workers = hit_order.workers
            }else{ // Ignore HITs that dont appear in the hit_order
                minihits.splice(i, 1);
                i-=1
            }
        }
    }
    for(let i in hits_order){
        if(hits_order[i].id == null)
            minihits.push({'batch_id':item.batch_id, 'position':hits_order[i].position, 'workers':hits_order[i].workers})
    }
    var hit_group = summarize_minihits(minihits, item.batch_status, item.hidden, item.batch_goal, item.batch_name)
    if(minihits.length) // MTURK API processes created hits for a bit -> cannot access instantly, so if we have a hit in DB but not in mturk-query ignore it
        render_surveys.push(hit_group)
})

var table = $('#project_table').DataTable({
    "language":{
        "url": datatables_translation
    },
    data: render_surveys,
    "createdRow": function( row, data, dataIndex ) {
        $(row).addClass('mainrow')
        if (data.batched) {
            $(row).addClass( 'batched' )

        }else{
            $(row).addClass( 'standard' )
        }
    },
    "columns": [ 
        {   "data": null,
            defaultContent: "",
            "searchable": false,
            "orderable": false,
        },
        {
            "data": null,
            "render": function(data, type, row){
                if(row.batched){
                    return row.name
                }else{
                    return row.Title
                }
            }
        },
        {
            "data": null,
            "render": function(data, type, row){
                var noAssComplete = row.NumberOfAssignmentsCompleted
                var noAssMax = row.MaxAssignments
                var noAssGoal = row.assignment_goal
                var noAssPending = row.NumberOfAssignmentsPending                        
                var noAssSubmitted = noAssMax - (row.NumberOfAssignmentsAvailable + noAssPending)

                if (row.batched){
                    var percentSubmitted = (noAssSubmitted/noAssGoal*100).toFixed(1)
                    return noAssSubmitted+"/"+noAssGoal+"("+noAssMax+")"+" ("+percentSubmitted+"%)P:"+noAssPending+", C:"+noAssComplete
                }
                else{
                    var percentSubmitted = (noAssSubmitted/noAssMax*100).toFixed(1)
                    return noAssSubmitted+"/"+noAssMax+" ("+percentSubmitted+"%)P:"+noAssPending+", C:"+noAssComplete
                }
            },
            "type": "amount-complete"
        },
        {
            "data": null,
            "render": function(data, type, row){
                return "<span val="+new Date(data.CreationTime).getTime()+">"+toDate(data.CreationTime)+"</span>" //necessary hack for DataTables sorting :(
            },
            "type": "date"
        },
        {
            "data": null,
            "render": function(data, type, row){
                if (data.Expiration == 'tbd')
                    return  "<span val=none>" + _('TBD') + "</span>"
                else
                    return "<span val="+new Date(data.Expiration).getTime()+">"+toDate(data.Expiration)+"</span>"
            },
            "type": "date"
        },
        { 
            "data": null,
            "visible": false,
            "render": function(data, type, row){  //This makes the infochild searchable, too
                return data.Description + data.HITStatus + data.Keywords + data.HITReviewStatus + data.HITId + data.HITTypeId
            }
        },
        {
            "data":null,
            "orderable": false,
            "render": function(){return ""},
            "width": "25%"
        },
        {
            "data": null,
            defaultContent: "",
            "orderable": false,
            "searchable": false,
            "render": function(data,type,row){
                if(data.batched){
                    return '<i class="fas fa-chevron-down"></i>'
                }
            }
        } 
    ],
    "order": [[ 1, 'asc' ]],
    "initComplete": function( settings, json ) {
        configure_header()
    }
});
// Hide hidden by default
$.fn.dataTable.ext.search.push(
    function hidden(settings, data, dataIndex) {
        var row_data = table.row(dataIndex).data()
        if(row_data.hidden)
            return false
        else
            return true
        }
);

/* https://datatables.net/plug-ins/api/row().show() */
$.fn.dataTable.Api.register('row().show()', function() {
        
    var page_info = this.table().page.info();
    // Get row index
    var new_row_index = this.index();
    // Row position
    var row_position = this.table().rows()[0].indexOf( new_row_index );
    // Already on right page ?
    if( row_position >= page_info.start && row_position < page_info.end ) {
        // Return row object
        return this;
    }
    // Find page number
    var page_to_display = Math.floor( row_position / this.table().page.len() );
    // Go to that page
    this.table().page( page_to_display ).draw('page');
    // Return row object
    return this;
});

$('i[data-toggle="tooltip"]').tooltip()

// TODO: finish
// TODO: dont save IDs etc in DOMs but get them via the row.data
table.rows().every( function(){ //Create 2 child rows and show BOTH(API restriction)
    
    if(this.data().batched){
        this.child(
                [
                    format_info(this.data()), // maybe change so that not added into td
                    format_slide(this.data())
                ]             
            ).show()
        this.child().first().addClass("info-row")
        this.child().last().addClass("slider-row").hide()
    }else{                
        this.child(format_info(this.data()),'info-row').show() // maybe change so that not added into td       
    }
})

table.on( 'order.dt search.dt', function () {
    table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
        cell.innerHTML = i+1+".";
    } );
} ).draw();       


function configure_header(){
    $("#project_table_length").parent("div").removeClass("col-md-6").addClass("col-md-3")
    $("#project_table_filter").parent("div").removeClass("col-md-6").addClass("col-md-3")
    var check_div = $("<div>").addClass("col-sm-12 col-md-6")
        .append('<div class="form-check form-check-inline">'+
                    '<label for="hide_hidden" class="form-check-label">'+_('Show hidden')+'</label>'+
                    '<input id="hide_hidden" type="checkbox" class="form-check-input" style="margin-left:1rem">'+
                '</div>')
        .append('<div class="pl-3 form-check form-check-inline">'+
                '<label for="hide_nonbatched" class="form-check-label">'+_('Show nonbatched')+'</label>'+
                '<input id="hide_nonbatched" type="checkbox" class="form-check-input" style="margin-left:1rem" checked>'+
            '</div>')
    $("#project_table_length").parent("div").after(check_div)

    $("#hide_hidden").on("click",function() {
        if(!$(this).prop("checked")){ // If not checked add filter function
            $.fn.dataTable.ext.search.push(
            function hidden(settings, data, dataIndex) {
                var row_data = table.row(dataIndex).data()
                if(row_data.hidden)
                    return false
                else
                    return true
                }
            );
        }else{ // If checked get filter function and remove it
            var index = getIndexOfFunc($.fn.dataTable.ext.search, "hidden")
            if(index==-1) return
            $.fn.dataTable.ext.search.splice(index, 1);
        }               
        table.draw();
    });    
    
    $("#hide_nonbatched").on("click",function() {
        if(!$(this).prop("checked")){ // If not checked add filter function
            $.fn.dataTable.ext.search.push(
            function batched(settings, data, dataIndex) {
                var row_data = table.row(dataIndex).data()
                if(row_data.batched)
                    return true
                else
                    return false
                }
            );
        }else{ // If checked get filter function and remove it
            var index = getIndexOfFunc($.fn.dataTable.ext.search, "batched")
            if(index==-1) return
            $.fn.dataTable.ext.search.splice(index, 1);
        }     
        table.draw();
    });    
}

function getIndexOfFunc(array, funcname){
    for(let i in array){
        if(array[i].name==funcname){
            return i
        }
    }
    return -1
}


$('#project_table').on('click', 'tr.info-row', function(event){ // if click on info row trigger click on DataTables-ParentRow
    if($(event.target).is(":button"))
        return            
    $(this).prev().trigger('click')
})

var animation_running = 0;
$('#project_table tbody').on('click', 'tr.batched[role="row"]', function (event) {
    if(!animation_running) // wait for both animations to finish
        animation_running = 1
    else
        return

    var tr = $(this).closest('tr');
    var row = table.row(tr);
    var slider_child = row.child().last()

    if ( tr.hasClass("shown") ) {          
        tr.removeClass('shown');      
        // This row is already open - close it
        $('div.slider', slider_child).slideUp( function () {
            
                slider_child.hide();
                animation_running-=0.5

        } );
        $('div.slider', slider_child).parent('td').animate({padding: '0'}, 300, function(){                    
            animation_running-=0.5
        });
    }
    else {
        slider_child.show();   
        tr.addClass('shown');         
        $('div.slider', slider_child).slideDown(function(){
            animation_running-=0.5
        });
        $('div.slider', slider_child).parent('td').animate({padding: '0.75rem'}, 300, function(){                    
            animation_running-=0.5
        });
    }
});

$('#project_table').on( 'click', '.delete-queued', function (event) {
    // should use row.data() instead of accessing html-data
    // make this implement a fetch to get the remaining lists and refresh the list
    
    (async () => {
        var slide_table = $(this).closest('table')
        var group_id = slide_table.data('group-id')
        var position = $(this).closest('tr').children("td:first").text()
        slide_table.find('button').attr('disabled', 'true')
        const rawResponse = await fetch('/db/delete-queued/'+group_id+'/'+position, {
            method: 'DELETE'
        });
        
        const content = await rawResponse.json();
        slide_table.find('button').removeAttr("disabled")
        if(content.success){
            $(this).closest('tr').remove()
            slide_table.children('tr').each(function(index){
                $(this).children('td:first').text(index+1)
            })
            show_alert(_("Success"), _("Successfully deleted queued HIT from Database."), "success")
        }else{
            var errormsg = ""

            if(content.type == 'locked'){
                tr = format_slide_row(content.hit)
                $(this).closest('tr').replaceWith(tr)
                errormsg = content.error
            }else if(content.type == 'not_found'){
                errormsg = content.error
            }
            show_alert(_("Error"), errormsg, "danger")
            
        }
        })();
} );

$('#project_table').on('click', '.cache-btn',function(event){
    var row = $(this).closest("tr.info-row").prev("tr")
    var data = table.row(row).data()
    $.alert({
        title: _('Archiving Batch!'),
        content: gt.strargs(_('Are you sure you want to archive the Batch "%1"?'), [data.name])+'<br>'+_('This will decrease the loading times but is also non reversable and you will not be able to modify the Batch anymore!'),
        buttons: {
            confirm:{
                text: _('confirm'),
                btnClass: 'btn-blue',
                action: function(){
                    $.alert({
                        title: _('Archiving Batch'),
                        content: _('Are you sure?'),
                        buttons:{
                            yes:{
                                text: _('yes'),
                                btnClass: 'btn-blue',
                                action: async function () {
                                    $('body').addClass('loading')
                                    const rawResponse = await fetch('/cache_batch/'+data.batch_id, {
                                        method: 'DELETE'
                                    });
                                    
                                    $('body').removeClass('loading')
                                    $('#loading-main').text(_('Archiving Batch. This may take some time depending on the size of the batch!'))
                                    const content = await rawResponse.json();
                                    if(content.success){
                                        table.row(row).remove()
                                        table.draw()
                                        show_alert(_("Success"), gt.strargs(_('Successfully archived Batch "%1"'), [data.name]), "success")
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
            }
        }
    });
})

$('#project_table').on('click', '.toggle-groupstatus', function(event){
    (async () => {
        var parent_row = $(this).closest('tr.info-row').prev()
        var batch_id = table.row(parent_row).data().batch_id
        const rawResponse = await fetch('/db/toggle_group_status/'+batch_id, {
            method: 'PATCH'
        });
        
        const content = await rawResponse.json();
        if (content.success){
            var btn_text = content.status=='active'?_("Pause"):_("Continue")
            $(this).closest('tr.info-row').find('.batch-status').text(content.status=='active'?_('Active'):_('Paused'))
            $(this).text(btn_text)
        }
    })();
})

$('#project_table').on('click','.hide_hit', function(event){
    (async () => {
        var button = $(this)
        var button_row = $(this).closest("tr.info-row")
        var parent_row = button_row.prev()
        var slider_row = button_row.next('tr.slider-row')   
        var hit_data = table.row(parent_row).data()
        var query=""
        if(hit_data.batched)
            query = hit_data.batch_id+"/True"
        else
            query = hit_data.HITId
        
        button.prop("disabled",true);
        const rawResponse = await fetch('/db/toggle_hit_visibility/'+query, {
            method: 'PATCH'
        });
        const content = await rawResponse.json();
        if (content.success){
            hit_data.hidden = content.hidden
            var btn_text = content.hidden?_("Show"):_("Hide")
            $(this).text(btn_text)
            // If we hid the row and we are not currently showing hidden rows we animate a fadeOut
            if(hit_data.hidden && !document.getElementById('hide_hidden').checked){
                var rows = parent_row.add(button_row)
                if(slider_row.is(':visible')){
                    rows = rows.add(slider_row)
                }
                rows.fadeOut("slow", function(){
                    parent_row.removeClass('shown').show()
                    button_row.show()
                    table.draw()
                    button.prop("disabled",false);
                })
            }else{
                table.draw()
                button.prop("disabled",false);
            }
        }
        })();
})

$('#project_table').on('click','.delete_hit', function(event){                  
    var button = $(this)
    var row = button.closest('tr.info-row').prev()
    var data = table.row(row).data()
    var id = data['HITId']

    $.alert({
    title: _('HIT Deletion!'),
    content: gt.strargs(_('Are you sure that you want to <b>delete</b> the HIT "%1"?'), [data.Title]) + '</br>' + _('Make sure to create a backup of your results first.'),
    buttons: {
        confirm:{
            text: _('confirm'),
            btnClass: 'btn-blue',
            action: function(){
                $.alert({
                    title: _('HIT Deletion'),
                    content: _('Are you sure?'),
                    buttons:{
                        yes:{
                            text: _('yes'),
                            btnClass: 'btn-blue',
                            action: async function () {   
                                const rawResponse = await fetch('/delete_hit/'+id, {
                                    method: 'DELETE'
                                });
                                const content = await rawResponse.json();
                                if(content.success){
                                    show_alert(_('Success'), _('The HIT was deleted successfully!'), 'success')
                                    table.row(row).remove()
                                    table.draw()
                                }
                                else{
                                    show_alert(_('Error'), content.error, 'danger')
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
        },
        cancel:{
            text: _('cancel'),
        }
    }
    });
})

async function testingstuff(){
    $('body').addClass('loading')
    var errors = []
    var checkboxes =  $(".checkbox-group:checked")
    var queue = []

    for(let i=0; i<50; i++){
        var assid = $(this).closest('tr').data('assid')
        var workerid = $(this).closest('tr').data('workerid')
        queue.push('Approving Assignment ' + (i+1))
        if(i % 2 || i % 3)
            queue.push('Softblocking Worker' + (i+1))
    }

    var lw = new LoadingWheel(50, queue)

    for(let i=0; i<50; i++){
        let rawResponse = await fetch('/testingstuff')
        let data = await rawResponse.json()
        lw.nextValue()
        if(i % 2 || i % 3){
            let rawResponse2 = await fetch('/testingstuff')
            let data2 = await rawResponse2.json()
            lw.nextValue()
        }
        lw.nextStep()
    }
    $('body').removeClass('loading')
}

$('#reject-selected').on('click', function(){
    $('body').addClass('loading')
    var errors = []
    var checkboxes =  $(".checkbox-group:checked")
    var queue = []
    checkboxes.each(function(){
        var assid = $(this).closest('tr').data('assid')
        var workerid = $(this).closest('tr').data('workerid')
        queue.push('Rejecting Assignment ' + assid)
        var softblock_btn = $(this).closest('td').next('td').find('.softblock-group')
        if(softblock_btn[0].checked)
            queue.push('Softblocking Worker' + workerid)
    })
    var lw = new LoadingWheel(checkboxes.length, queue)
    var count = checkboxes.length
    checkboxes.each(async function(){
        var assid = $(this).closest('tr').data('assid')
        var workerid = $(this).closest('tr').data('workerid')
        const rawResponse = await fetch('/reject_assignment/'+assid+'/'+workerid,{
            method: 'PATCH'
        })
        const data = await rawResponse.json()
        if(!data.success){
            errors.push({'id': assid, 'error': data.error})
        }
        lw.nextValue()
        var softblock_btn = $(this).closest('td').next('td').find('.softblock-group')
        if(softblock_btn[0].checked){
            const rawResponse2 = await fetch('/api/softblock/'+workerid,{
                method: 'PATCH'
            })
            const data2 = await rawResponse2.json()
            if(!data2.success){
                errors.push({'id': workerid, 'error': data.error})
            }
            lw.nextValue()
        }
        lw.nextStep()
        if (!--count) alert_cfg()
    })
    $('body').removeClass('loading')

    function alert_cfg(){
        if(errors.length == 0){
            show_alert(_('Success'), _('The selected assignments were successfully rejected!'), 'success')
        }else{
            string = _("The following errors occured:")+" </br>"
            for(let i=0; i<errors.length; i++){
                string += gt.strargs(_('AssignmentId %1: %2'), [errors[i]['id'], errors[i]['error']]) +'</br>'
            }
            show_alert(_('Error'), string, 'danger')
        }    
        $('#progressmodal').modal('hide')
    }
})

$('#approve-selected').on('click', function(){
    $('body').addClass('loading')
    var errors = []
    var checkboxes =  $(".checkbox-group:checked")
    var queue = []
    checkboxes.each(function(){
        var assid = $(this).closest('tr').data('assid')
        var workerid = $(this).closest('tr').data('workerid')
        queue.push(_('Approving Assignment ') + assid)
        var softblock_btn = $(this).closest('td').next('td').find('.softblock-group')
        if(softblock_btn[0].checked)
            queue.push(_('Softblocking Worker') + workerid)
    })
    var lw = new LoadingWheel(checkboxes.length, queue)
    var count = checkboxes.length
    checkboxes.each(async function(){
        var assid = $(this).closest('tr').data('assid')
        var workerid = $(this).closest('tr').data('workerid')
        const rawResponse = await fetch('/approve_assignment/'+assid+'/'+workerid,{
            method: 'PATCH'
        })
        const data = await rawResponse.json()
        if(!data.success){
            errors.push({'id': assid, 'error': data.error})
        }
        lw.nextValue()
        var softblock_btn = $(this).closest('td').next('td').find('.softblock-group')
        if(softblock_btn[0].checked){
            const rawResponse2 = await fetch('/api/softblock/'+workerid,{
                method: 'PATCH'
            })
            const data2 = await rawResponse2.json()
            if(!data2.success){
                errors.push({'id': workerid, 'error': data.error})
            }
            lw.nextValue()
        }
        lw.nextStep()
        if (!--count) alert_cfg()
    })
    $('body').removeClass('loading')

    function alert_cfg(){
        if(errors.length == 0){
            show_alert(_('Success'), _('The selected assignments were successfully approved!'), 'success')
        }else{
            var string = _("The following errors occured:")+" </br>"
            for(let i=0; i<errors.length; i++){
                string += gt.strargs(_('AssignmentId %1: %2'), [errors[i]['id'], errors[i]['error']]) +'</br>'
            }
            show_alert(_('Error'), string, 'danger')
        }    
        $('#progressmodal').modal('hide')
    }
})

$('#checkbox-toggler').on('click', function(){
    if(this.checked)
        $('input.checkbox-group').prop('checked', true).trigger('change')
    else
        $('input.checkbox-group').prop('checked', false).trigger('change')
})

$('#progressmodal').on('hidden.bs.modal', function (e) {
    var modal = $(this)
    $('#checkbox-toggler').prop('checked',false)
    modal.find(".info-empty").empty()
    modal.find(".modal-body tbody").empty()
    modal.find(".modal-title").text(_("Loading"))
    $('button.selected-action').prop('disabled', true)
})

$('#progressmodal').on('change', '.checkbox-group', function(){
    var any_checked = false
    $(this).each(function(){
        if(this.checked){
            any_checked = true
            return false
        }
    })
    if(any_checked)
        $('button.selected-action').prop('disabled', false)
    else
        $('button.selected-action').prop('disabled', true)
})

$('#progressmodal').on('show.bs.modal', async function(event){
    var modal = $(this)
    var button = $(event.relatedTarget)
    if (button.data('batched')){
        var position = button.data("position")
        var id = button.data("id")
        modal.find(".modal-title").text(_("Progress for ")+position+". HIT")
    } else {
        row = button.closest('tr.info-row').prev()
        var row_data = table.row(row).data()
        var id = row_data['HITId']
        modal.find(".modal-title").text(_("Progress for HIT ")+row_data.Title)
    }
    const rawResponse = await fetch("/list_assignments/"+id);
    const data = await rawResponse.json()

    var all_times = []
    if(data.length == 0){
        var row = $('<div class="row p-5">')
        row.append('<div class="col-lg-12 text-center"><h2>' + _('No Results have been submitted') + '</h2></div>')
        modal.find(".info-empty").append(row)
        $('button.selected-action').hide()
    }else{
        $('button.selected-action').show()
        tbody = modal.find(".modal-body tbody")
        data.forEach(function(elem, index){
            //could use date to show GMT+2 time
            var acceptTime = new Date(elem.AcceptTime)                        
            var submitTime = new Date(elem.SubmitTime)

            var timeTakenSec = (submitTime - acceptTime) / 1000  //1000: milli to seconds 
            all_times.push(timeTakenSec)

            var timeTakenRounded = (Math.round(timeTakenSec/60*10)/10).toFixed(1) // Converts sec to min and rounds minutes to 1 digit after comma            

            var checkbox, softblockbox;
            if (elem.AssignmentStatus == 'Submitted'){
                checkbox = $('<input type="checkbox" class="checkbox-group">')
                softblockbox= $('<input type="checkbox" class="softblock-group">')
            }else{
                checkbox = '<input type="checkbox" disabled>'
                softblockbox = '<input type="checkbox" disabled>'
            }

            var row = $('<tr>').addClass("border-bottom")
            row.append($('<td class="py-3">').text(index+1+".")).data('assid', elem.AssignmentId).data('workerid', elem.WorkerId)
                .append($('<td>').addClass("worker").text(elem.WorkerId))
                .append($('<td>').text(elem.Answer))
                .append($('<td>').text(elem.AssignmentStatus))
                .append($('<td>').addClass("bonus").text('-'))
                .append($('<td class="time-taken">').data('seconds', timeTakenSec).text(timeTakenRounded + 'min'))
                .append($('<td>').append(toDate(elem.AcceptTime)))
                .append($('<td>').append(toDate(elem.SubmitTime)))
                .append($('<td>').append(checkbox))
                .append($('<td>').append(softblockbox))            
            tbody.append(row)
        })

        var avg_time = average(all_times)
        var std = standardDeviation(all_times)
        var lower_bound = avg_time - std
        var upper_bound = avg_time + std
        $('.time-taken').each(function(){
            if($(this).data('seconds') < lower_bound || $(this).data('seconds') > upper_bound){
                $(this).addClass('text-danger font-weight-bold')
            }
        })
        // Demo for this : https://jsfiddle.net/0m9pw3rx/5/


        const rawResponse2 = await fetch("/list_payments/"+id)
        const data2 = await rawResponse2.json()
        data2.forEach(function(elem){
            // Get WorkerId of BonusPayment-data
            var workerid = elem.WorkerId
            var bonus = elem.BonusAmount

            //look through progressmodaltables rows and change bonus-td if workerIds match
            $("table.progress-table tbody tr").each(function(){
                if($(this).find(".worker").text() == workerid)
                    $(this).find(".bonus").text("$"+bonus)
            })
        })

    }        
})

$('#csvmodal').on('hidden.bs.modal', function(event){
    var modal = $(this)
    $("#uploadform #file").val('').removeClass("error")
    $("#uploadform label.error").empty()
    $("#uploadform div.error").empty()
    $("#uploadform div.success").empty()  
    modal.find(".modal-body tbody").empty()
})

$('#csvmodal').on('show.bs.modal', function(event){
    var modal = $(this)
    var button = $(event.relatedTarget)
    var tbody = modal.find(".modal-body tbody")
    var row = button.closest('tr.info-row').prev()
    var data = table.row(row).data()
    $("#hit_batched").val(data.batched)
    $("#hit_identifier").val(data.batched?data.batch_id:data.HITId)
    modal.find(".modal-title").text(_("CSV Actions for ") + data.Title)
    if (data.batched)
        href = "/export/"+data.batch_id
    else
        href = "/export/"+data.HITId
    
    $("#export-all").attr("href", href+"/all")
    $("#export-submitted").attr("href", href+"/submitted")
})

$('#qualmodal').on('hidden.bs.modal', function(event){
    var modal = $(this)
    modal.find(".modal-body tbody").empty()
    modal.find(".info-empty").empty()
    modal.find(".modal-title").text(_('Loading'))
})

$('#qualmodal').on('show.bs.modal', function(event){
    var modal = $(this)
    var button = $(event.relatedTarget)
    var tbody = modal.find(".modal-body tbody")
    var row = button.closest('tr.info-row').prev()
    var data = table.row(row).data()
    modal.find(".modal-title").text(_("Qualifications for ") + data.Title)
    // Iterate over each Qualification of HIT
    
    if(!data.QualificationRequirements.length){
        var empty_row = $('<div class="row p-5">')
        empty_row.append('<div class="col-lg-12 text-center"><h2>'+_('No Qualifications are assigned to this HIT')+'</h2></div>')
        modal.find(".info-empty").append(empty_row)
    }else{
        data.QualificationRequirements.forEach(function(elem, index){
            var table_qual_id = elem.QualificationTypeId
            var value = "-"

            if(elem.hasOwnProperty('IntegerValues')){
                value=""
                elem.IntegerValues.forEach(function(val){
                    value+= (val+" ")
                })
            }
            if(elem.hasOwnProperty('LocaleValues')){
                value=""
                elem.LocaleValues.forEach(function(val){
                    value+= (val.Country+" ")
                })
            }

            var qual_row = $('<tr>').addClass("border-bottom")
                .append($('<td>').append($("<div class='py-3'>").text(index+1+".")))
                //.append($('<td>').append($("<div>").text(table_qual_id)))
                .append($('<td>').addClass("qual-name").text(_("Batch-Qualification, reload the Page to show the actual Name")))
                .append($('<td>').text(elem.Comparator))
                .append($('<td>').text(value))
                .append($('<td>').text(elem.ActionsGuarded))
            //Check if Id is of adult or master type
            if(table_qual_id == master_id){
                qual_row.find(".qual-name").text(_('Masters'))
            }else if(table_qual_id == master_id_sandbox){
                qual_row.find(".qual-name").text(_('Masters Sandbox'))
            }else if(table_qual_id == adult_id){
                qual_row.find(".qual-name").text(_('Adult Content'))
            }else{
                //loop over all qualifications to get the name
                for(let i in quals){
                    if(quals[i].QualificationTypeId==table_qual_id){
                        qual_row.find(".qual-name").text(quals[i].Name)
                    }
                }
            }
            qual_row.children(".qual-name").removeAttr('class')
            tbody.append(qual_row)
        })
    }   
})

$("#uploadbtn").on("click", async function(){
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

    const rawResponse = await fetch('/upload', { 
        method: 'POST',
        body: formData
        })
    const json = await rawResponse.json()
    $('body').removeClass("loading")
    if(json.success){
        console.log(json)
        // Adding Approved/Rejected, BonusPaid/softblocked                       
        var row = $("<div>").addClass("row")
        var col = $("<div>").addClass("col-3")
        var row_one = row.clone()
        row_one.append(col.clone().text(_("Approved")))
                .append(col.clone().text(json.data.approved))
                .append(col.clone().text(_("Rejected")))
                .append(col.clone().text(json.data.rejected))

        var row_two = row.clone()                        
        row_two.append(col.clone().text(_("Bonus paid")))
                .append(col.clone().text("$"+json.data.bonus))
                .append(col.clone().text(_("Softblocked")))
                .append(col.clone().text(json.data.softblocked))
        
        $("#uploadform div.success").append(row_two).append(row_one)
        
        // Adding warnings if any
        // Why do Dicts in JS not have an inbuilt method to check if empty, or atleast a length?
        if(Object.keys(json.warnings).length > 0){
            $("#uploadform div.error").append('<h4>'+_('Warnings')+':<h4>')
            for(let i in json.warnings){
                console.log(i)
                var li = $('<li>').text(_("Row ")+i)
                var ul = $('<ul>')
                for(let j in json.warnings[i]){
                    var row_li = $('<li>').text(json.warnings[i][j])
                    ul.append(row_li)
                }
                $("#uploadform div.error").append($('<ul>').append(li.append(ul)))                                
            }
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


$.fn.dataTable.ext.type.order['amount-complete-pre'] = function ( data ) {
    var percentage = data.substring(data.indexOf(" (")+2, data.indexOf("%)")) // isolate percentage
    return percentage
};

$.fn.dataTable.ext.type.order['date-pre'] = function ( data ) {
    var value = $(data).attr('val')
    if(isNaN(value)){
        return Number.MAX_SAFE_INTEGER
    }else{
        return parseInt(value)
    }
};


function format_info ( data ) {     

    var container = $("<div class='container' style='float-left'>")

    if(data.batched){
        var qualificationbutton = '<button type="button" class="btn btn-sm btn-info" data-toggle="modal" data-target="#qualmodal">'+_('CLICK')+'</button>'
        var hidebtn = '<button type="button" class="btn btn-info hide_hit">'+ (data["hidden"]?_("Show"):_("Hide")) +'</button>'         
        var csv_modal_btn = '<button type="button" class="btn btn-info" data-toggle="modal" data-target="#csvmodal">'+_('CSV-Actions')+'</button>'
        var group_id = data.batch_id
        var query = data.batch_id+'/True'
        var toggle_status_btn = '<button type="button" class="btn btn-info toggle-groupstatus">'+ (data["batch_status"]?_("Pause"):_("Continue")) +'</button>'
        var cache_btn = '<button type="button" class="btn btn-info cache-btn">'+_('Archive')+'</button>'
        var batch_status = data['batch_status'] ? _('Active'):_('Paused')
        var row_one = $('<div class="row mt-2">'+
            '<div class="col-2">'+_('Title')+':</div>'+
            '<div class="col-4">'+data['Title']+'</div>'+
            '<div class="col-2">'+_('Reward')+':</div>'+
            '<div class="col-2">$'+data['Reward']+'</div>'+
            '<div class="col-2">'+csv_modal_btn+'</div>'+
        '</div>')

        var row_two = $('<div class="row mt-2">'+
            '<div class="col-2">'+_('Description')+':</div>'+
            '<div class="col-4">'+data['Description']+'</div>'+
            '<div class="col-2">'+_('MiniBatched')+':</div>'+
            '<div class="col-2">'+_('Yes, ID')+': '+data['batch_id']+'</div>'+
            '<div class="col-2">'+cache_btn+'</div>'+
        '</div>')

        var row_three = $('<div class="row mt-2">'+
            '<div class="col-2">'+_('Keywords')+':</div>'+
            '<div class="col-4">'+data['Keywords']+'</div>'+
            '<div class="col-2">'+_('Batch-Status')+':</div>'+
            '<div class="col-2 batch-status">'+batch_status+'</div>'+
            '<div class="col-2">'+toggle_status_btn+'</div>'+
        '</div>')

        var row_four = $('<div class="row mt-2">'+
            '<div class="col-2">'+_('Qualifications')+':</div>'+
            '<div class="col-4">'+qualificationbutton+'</div>'+
            '<div class="col-2">'+_('HITTypeId')+':</div>'+
            '<div class="col-2">'+data['HITTypeId']+'</div>'+
            '<div class="col-2">'+hidebtn+'</div>'+
        '</div>')
    }
    else{
        var qualificationbutton = '<button type="button" class="btn btn-sm btn-success" data-toggle="modal" data-target="#qualmodal">'+_('CLICK')+'</button>'
        var hidebtn = '<button type="button" class="btn btn-success hide_hit">'+ (data["hidden"]?_("Show"):_("Hide")) +'</button>'         
        var csv_modal_btn = '<button type="button" class="btn btn-success" data-toggle="modal" data-target="#csvmodal">'+_('CSV-Actions')+'</button>'
        var result_btn = '<button type="button" class="btn btn-success" data-toggle="modal" data-target="#progressmodal">'+_('Results')+'</button>'
        var delbtn = '<button type="button" class="btn btn-secondary delete_hit">'+_('Delete')+'</button>'
        var query = data.HITId

        var row_one = $('<div class="row mt-2">'+
            '<div class="col-2 mt-2">'+_('Description')+':</div>'+
            '<div class="col-2 mt-2">'+data['Description']+'</div>'+
            '<div class="col-2 mt-2">'+_('HITId')+':</div>'+
            '<div class="col-4 mt-2">'+data['HITId']+'</div>'+
            '<div class="col-2 mt-2">'+csv_modal_btn+'</div>'+
        '</div>')

        var row_two = $('<div class="row mt-2">'+
            '<div class="col-2 mt-2">'+_('Keywords')+':</div>'+
            '<div class="col-2 mt-2">'+data['Keywords']+'</div>'+
            '<div class="col-2 mt-2">'+_('HITTypeId')+':</div>'+
            '<div class="col-4 mt-2">'+data['HITTypeId']+'</div>'+
            '<div class="col-2 mt-2">'+result_btn+'</div>'+
        '</div>')

        var row_three = $('<div class="row mt-2">'+
            '<div class="col-2 mt-2">'+_('Reward')+':</div>'+
            '<div class="col-2 mt-2">$'+data['Reward']+'</div>'+
            '<div class="col-2 mt-2">'+_('HIT-Status')+':</div>'+
            '<div class="col-4 mt-2">'+data['HITStatus']+'</div>'+
            '<div class="col-2 mt-2">'+delbtn+'</div>'+
        '</div>')

        var row_four = $('<div class="row mt-2">'+
            '<div class="col-2">'+_('Qualifications')+':</div>'+
            '<div class="col-2">'+qualificationbutton+'</div>'+
            '<div class="col-2">'+_('MiniBatched')+':</div>'+
            '<div class="col-4">'+_('No')+'</div>'+
            '<div class="col-2">'+hidebtn+'</div>'+
        '</div>')
        
    }
    return container.append(row_one).append(row_two).append(row_three).append(row_four)
}

function format_slide ( data ) {
    // `d` is the original data object for the row
    var group_id = data.batch_id
    var data = data.minihits
    var $table = $(' <table cellpadding="5" cellspacing="0" border="0" style="padding-left:50px;">').addClass('minihit-table')
    $table.data('group-id', group_id)
    
    for(let i in data){
        var hit = data[i]
        var $row = format_slide_row(hit)
        $table.append($row)
    }
    var $slider = $('<div>').addClass('slider').append( $table)
    return $slider
}

function format_slide_row(hit){
    if(hit.hasOwnProperty('CreationTime')){
        var ass_submitted = hit.MaxAssignments - (hit.NumberOfAssignmentsAvailable + hit.NumberOfAssignmentsPending)

        var $tr = $('<tr class="minihitrow running">')
        $tr.append($('<td>').text(hit.position)) //hit.position should be same as i always
        $tr.append($('<td>').text(hit.HITStatus))
        $tr.append($('<td>').text(ass_submitted+'/'+hit.MaxAssignments+' , P: '+hit.NumberOfAssignmentsPending+', C: '+hit.NumberOfAssignmentsCompleted))
        $tr.append($('<td>').text(hit.CreationTime))
        $tr.append($('<td>').text(hit.Expiration))
        var $progressbtn = $('<button type="button" data-toggle="modal" data-target="#progressmodal">').data("id",hit.HITId).data("position",hit.position).data("batched", true)
            .addClass("btn btn-sm btn-info").append('<i class="fas fa-tasks"></i>')
        $tr.append($('<td>').append($progressbtn))
    }else{
        var $tr = $('<tr class="minihitrow queued">')
        $tr.append($('<td>').text(hit.position)) //hit.position should be same as i always
        $tr.append($('<td>').text(_('Queued')))
        $tr.append($('<td>').text('0/'+hit.workers))
        $tr.append($('<td>'))
        $tr.append($('<td>'))
        var $delbtn = $('<button type=button>').addClass("btn btn-sm btn-danger delete-queued").append('<i class="fa fa-trash"></i>')                   

        $tr.append($('<td>').addClass('minihittd').append($delbtn))                
    }
    return $tr
}


function compare( a, b ) {
    if ( a.position < b.position ){
        return -1;
    }
    if ( a.position > b.position ){
        return 1;
    }
    return 0;
}

function summarize_minihits(array, status, hidden, goal, name){ //take array of minihits and returns hitgroup with an informationoverview
    var hitgroup = {}
    hitgroup.name = name
    hitgroup.assignment_goal = goal
    hitgroup.NumberOfAssignmentsAvailable = 0
    hitgroup.NumberOfAssignmentsPending = 0
    hitgroup.NumberOfAssignmentsCompleted = 0
    hitgroup.MaxAssignments = 0
    hitgroup.batched = true
    hitgroup.hidden = hidden
    hitgroup.batch_status = (status == 'active') ? true : false
    array.sort(compare)
    for(let i = 0; i < array.length; i++){
        if(i == 0){ // the first minihit should never be queued -> can savely access attributes
            hitgroup.CreationTime = array[i].CreationTime
            hitgroup.Title = array[i].Title
            hitgroup.Description = array[i].Description
            hitgroup.Keywords = array[i].Keywords
            hitgroup.HITTypeId = array[i].HITTypeId
            hitgroup.AssignmentDurationInSeconds = array[i].AssignmentDurationInSeconds
            hitgroup.AutoApprovalDelayInSeconds = array[i].AutoApprovalDelayInSeconds
            hitgroup.Reward = array[i].Reward
            hitgroup.QualificationRequirements = array[i].QualificationRequirements
            hitgroup.batch_id = parseInt(array[i].RequesterAnnotation.substr(5))
        }
        if(i == array.length-1){ // if the last hit of a batch is still queued we can only guess the expiration date of the "entire" batch
            if(array[i].hasOwnProperty('CreationTime'))
                hitgroup.Expiration = array[i].Expiration
            else
                hitgroup.Expiration = "tbd"
        }
        if(!array[i].hasOwnProperty('CreationTime')){ // unpublished hits only have 2 attributes, workers, position
            hitgroup.MaxAssignments +=array[i].workers
            hitgroup.NumberOfAssignmentsAvailable +=array[i].workers
            continue
        }
        hitgroup.NumberOfAssignmentsAvailable += array[i].NumberOfAssignmentsAvailable
        hitgroup.NumberOfAssignmentsPending += array[i].NumberOfAssignmentsPending
        hitgroup.NumberOfAssignmentsCompleted += array[i].NumberOfAssignmentsCompleted
        hitgroup.MaxAssignments += array[i].workers
        
        delete array[i].Title
        delete array[i].Description
        delete array[i].Keywords
        delete array[i].AssignmentDurationInSeconds
        delete array[i].AutoApprovalDelayInSeconds
        delete array[i].HITGroupId
        delete array[i].Reward
        delete array[i].QualificationRequirements
        delete array[i].Question
    }
    hitgroup.minihits = array
    return hitgroup
}

function get_element_with_value(json, key, value){
    for(let item_index in json){
        var item = json[item_index]
        if(item.hasOwnProperty(key) && item[key] == value){
            return item
        }
    }
    return null
}

function get_elements_with_value(json, key, value){
    var list = []
    json.forEach((item) => {
        if(item.hasOwnProperty(key) && item[key] == value)
            list.push(item) 
    });
    return list
};

$(function(){
    if(createdhit != null){
        // Hide hidden by default
        table.rows().every( function(){
            // check if either row or sliderchild has ID
            var data = this.data()
            if( (data.hasOwnProperty("HITId") && data["HITId"] == createdhit) || get_element_with_value(data.minihits,"HITId", createdhit) ){
                this.show()
                var $row = $(this.node())
                $('html').animate({
                    'scrollTop': $row.offset().top - 500
                }, 2000, 'swing', function(){                
                    $row.addClass("highlight")
                    $row.next().addClass("highlight")
                    setTimeout(function(){$(".highlight").removeClass("highlight")}, 3000)
                })
            }
        })
    }
})