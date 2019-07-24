
        render_surveys=[]
        
        for(hit_index in surveys){ // Add HITs that are not to be batched to 
            hit = surveys[hit_index]
            if(hit.hasOwnProperty('RequesterAnnotation') && hit['RequesterAnnotation'].includes('batch'))
                continue
            hit.batched = false

            for (i in hidden_hits){
                if (hidden_hits[i][0]==hit.HITId)
                    hit.hidden=true
            }
            render_surveys.push(hit)
        }
        
        //TODO CHANGE THIS 
        ordering.forEach((item) => { //TODO change, maybe add group parameter to ordering
            minihits = get_elements_with_value(surveys, "RequesterAnnotation", "batch"+item.batch_id)
            hits_batch_id = item.batch_id
            hits_order = item.hits
            for(i=0; i<minihits.length; i++){
                hit = minihits[i] 
                if(hit.hasOwnProperty("HITId")){ //if hit is not queued it has an ID
                    hit_order = get_element_with_value(hits_order, "id", hit.HITId)
                    if(hit_order){
                        hit.position = hit_order.position
                        hit.workers = hit_order.workers
                    }else{ // Ignore HITs that dont appear in the hit_order
                        minihits.splice(i, 1);
                        i-=1
                    }
                }
            }
            for(i in hits_order){
                if(hits_order[i].id == null)
                    minihits.push({'batch_id':item.batch_id, 'position':hits_order[i].position, 'workers':hits_order[i].workers})
            }
            hit_group = summarize_minihits(minihits, item.batch_status, item.hidden, item.batch_goal, item.batch_name)
            if(minihits.length) // MTURK API processes created hits for a bit -> cannot access instantly, so if we have a hit in DB but not in mturk-query ignore it
                render_surveys.push(hit_group)
        })

        var table = $('#project_table').DataTable({
            data: render_surveys,
            "createdRow": function( row, data, dataIndex ) {
                $(row).addClass('mainrow')
                if (data.batched) {
                    $(row).addClass( 'batched' ) //TODO: work more with jquery data()

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
                /*{ "data": "Title" },*/
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
                        noAssComplete = row.NumberOfAssignmentsCompleted
                        noAssMax = row.MaxAssignments
                        noAssGoal = row.assignment_goal
                        noAssPending = row.NumberOfAssignmentsPending                        
                        noAssSubmitted = noAssMax - (row.NumberOfAssignmentsAvailable + noAssPending)

                        if (row.batched){
                            percentSubmitted = (noAssSubmitted/noAssGoal*100).toFixed(1)
                            return noAssSubmitted+"/"+noAssGoal+"("+noAssMax+")"+" ("+percentSubmitted+"%)P:"+noAssPending+", C:"+noAssComplete
                        }
                        else{
                            percentSubmitted = (noAssSubmitted/noAssMax*100).toFixed(1)
                            return noAssSubmitted+"/"+noAssMax+" ("+percentSubmitted+"%)P:"+noAssPending+", C:"+noAssComplete
                        }
                    },
                    "type": "amount-complete"
                },
                { "data": "CreationTime" },
                { "data": "Expiration" } ,
                { 
                    "data": null,
                    "visible": false,
                    "render": function(data, type, row){  //This makes the infochild searchable, too
                        return data.Description + data.HITStatus + data.Keywords + data.HITReviewStatus + data.HITId + data.HITTypeId
                    }
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
            "order": [[ 1, 'asc' ]]
        });

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
                this.child().last().hide()
            }else{                
                this.child(format_info(this.data()),'info-row').show() // maybe change so that not added into td       
            }
        })

        table.on( 'order.dt search.dt', function () {
            table.column(0, {search:'applied', order:'applied'}).nodes().each( function (cell, i) {
                cell.innerHTML = i+1+".";
            } );
        } ).draw();       

        if(createdhit != null){
            table.rows().every( function(){
                // check if either row or sliderchild has ID
                // TODO: wth did I do with get_element_with_value
                data = this.data()
                if( (data.hasOwnProperty("HITId") && data["HITId"] == createdhit) || get_element_with_value(data.minihits,"HITId", createdhit) ){
                    this.show()
                    $row = $(this.node())
                    $('html, body').animate({
                        'scrollTop': $row.offset().top - 500
                    }, 2000, 'swing', function(){
                        $row.addClass("highlight")
                        $row.next().addClass("highlight")
                        setTimeout(function(){$(".highlight").removeClass("highlight")}, 3000)
                    })
                }
            })
        }
        

        $("#project_table_length").parent("div").removeClass("col-md-6").addClass("col-md-3")
        $("#project_table_filter").parent("div").removeClass("col-md-6").addClass("col-md-3")
        check_div = $("<div>").addClass("col-sm-12 col-md-6")
            .append('<div class="form-check form-check-inline">'+
                        '<label for="hide_hidden" class="form-check-label">Show hidden</label>'+
                        '<input id="hide_hidden" type="checkbox" class="form-check-input" style="margin-left:1rem">'+
                    '</div>')
            .append('<div class="pl-3 form-check form-check-inline">'+
                    '<label for="hide_nonbatched" class="form-check-label">Show nonbatched</label>'+
                    '<input id="hide_nonbatched" type="checkbox" class="form-check-input" style="margin-left:1rem">'+
                '</div>')
        $("#project_table_length").parent("div").after(check_div)

        function getIndexOfFunc(array, funcname){
            for (i in array){
                if(array[i].name==funcname){
                    return i
                }
            }
            return -1
        }
        
        //TODO: need parameter for hide/unhide
        $("#hide_hidden").on("click",function() {
            if(!$(this).prop("checked")){ // If not checked add filter function
                $.fn.dataTable.ext.search.push(
                function hidden(settings, data, dataIndex) {
                    row_data = table.row(dataIndex).data()
                    if(row_data.hidden)
                        return false
                    else
                        return true
                    }
                );
            }else{ // If checked get filter function and remove it
                index = getIndexOfFunc($.fn.dataTable.ext.search, "hidden")
                if(index==-1) return
                $.fn.dataTable.ext.search.splice(index, 1);
            }               
            table.draw();
        });

        $("#hide_hidden").click().click() // check and uncheck to initialize filter above

        $("#hide_nonbatched").on("click",function() {
            if(!$(this).prop("checked")){ // If not checked add filter function
                $.fn.dataTable.ext.search.push(
                function batched(settings, data, dataIndex) {
                    row_data = table.row(dataIndex).data()
                    if(row_data.batched)
                        return true
                    else
                        return false
                    }
                );
            }else{ // If checked get filter function and remove it
                index = getIndexOfFunc($.fn.dataTable.ext.search, "batched")
                if(index==-1) return
                $.fn.dataTable.ext.search.splice(index, 1);
            }     
            table.draw();
        });

        $("#hide_nonbatched").click() // Default: show nonbatched

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
                slide_table = $(this).closest('table')
                group_id = slide_table.data('group-id')
                position = $(this).closest('tr').children("td:first").text()
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
                    show_alert("SUCCESS!", "Successfully deleted queued HIT from Database.", "success")
                }else{
                    errormsg = ""

                    if(content.type == 'locked'){
                        tr = format_slide_row(content.hit)
                        $(this).closest('tr').replaceWith(tr)
                        errormsg = content.error
                    }else if(content.type == 'not_found'){
                        errormsg = content.error
                    }
                    show_alert("ERROR!", errormsg, "danger")
                    
                }
              })();
        } );

        $('#project_table').on('click', '.cache-btn',function(event){
            console.log("asd")
            row = $(this).closest("tr.info-row").prev("tr")
            data = table.row(row).data()
            console.log(data)
            $.alert({
                title: 'Batch Caching!',
                content: 'Are you sure you want to cache the Batch "'+data.name+'"?<br>This will decrease the loading times but is also non reversable and you will not be able to modify the Batch anymore!',
                buttons: {
                    confirm:{
                        btnClass: 'btn-blue',
                        action: function(){
                            $.alert({
                                title: 'Really?',
                                content: 'Are you sure?',
                                buttons:{
                                    yes:{
                                        btnClass: 'btn-blue',
                                        action: async function () {
                                            const rawResponse = await fetch('/cache_batch/'+data.batch_id, {
                                                method: 'DELETE'
                                            });
                                              
                                            const content = await rawResponse.json();
                                            if(content.success){
                                                table.row(row).remove()
                                                table.draw()
                                                show_alert("Success", 'Successfully cached Batch "'+data.name+'"', "success")
                                            }else{
                                                show_alert("Error", 'Something went wrong: '+content.error, "danger")
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
        })

        $('#project_table').on('click', '.toggle-groupstatus', function(event){
            (async () => {
                parent_row = $(this).closest('tr.info-row').prev()
                batch_id = table.row(parent_row).data().batch_id
                const rawResponse = await fetch('/db/toggle_group_status/'+batch_id, {
                  method: 'PATCH'
                });
                
                const content = await rawResponse.json();
                if (content.success){
                    btn_text = content.status=='active'?"Pause":"Continue"
                    $(this).closest('tr.info-row').find('.batch-status').text(content.status=='active'?'Active':'Paused')
                    $(this).text(btn_text)
                }
            })();
        })

        $('#project_table').on('click','.hide_hit', function(event){
            (async () => {
                parent_row = $(this).closest("tr.info-row").prev()
                hit_data = table.row(parent_row).data()
                query=""
                if(hit_data.batched)
                    query = hit_data.batch_id+"/True"
                else
                    query = hit_data.HITId
                
                const rawResponse = await fetch('/db/toggle_hit_visibility/'+query, {
                    method: 'PATCH'
                });
                const content = await rawResponse.json();
                if (content.success){
                    hit_data.hidden = content.hidden
                    btn_text = content.hidden?"Show":"Hide"
                    $(this).text(btn_text)
                }
                table.draw()
              })();
        })

        //TODO: TEST WITH MULTIPLE WORKER SUBMISSIONS FOR EACH MINIHIT
        $('#progressmodal').on('show.bs.modal',async function(event){
            var modal = $(this)
            var button = $(event.relatedTarget)
            var position = button.data("position")
            var id = button.data("id")
            modal.find(".modal-title").text("Progress for "+position+". HIT")
            modal.find("#progress-empty").empty()
            tbody = modal.find(".modal-body tbody").empty()
            const rawResponse = await fetch("/list_assignments/"+id);
            const data = await rawResponse.json()
            
            if(data.length == 0){
                row = $('<div class="row p-5">')
                row.append('<div class="col-lg-12 text-center"><h2>No Results have been submitted</h2></div>')
                modal.find("#progress-empty").append(row)
            }else{
                data.forEach(function(elem, index){
                    //could use date to show GMT+2 time
                    acceptTime = new Date(elem.AcceptTime)                        
                    submitTime = new Date(elem.SubmitTime)
    
                    timeTakenMin = (submitTime - acceptTime) / 1000 / 60  //1000: milli to seconds; 60: seconds to minutes
                    timeTakenRounded = (Math.round(timeTakenMin*10)/10).toFixed(1) // Rounds minutes to 1 digit after comma
    
                    row = $('<tr>').addClass("border-bottom")
                    row.append($('<td>').text(index+1+"."))
                        .append($('<td>').addClass("worker").text(elem.WorkerId))
                        .append($('<td>').text(elem.Answer))
                        .append($('<td>').text(elem.AssignmentStatus))
                        .append($('<td>').addClass("bonus").text('-'))
                        .append($('<td>').text(timeTakenRounded + 'min'))
                        .append($('<td>').text(elem.AcceptTime))
                        .append($('<td>').text(elem.SubmitTime))
                    tbody.append(row)
                })

                const rawResponse2 = await fetch("/list_payments/"+id)
                const data2 = await rawResponse2.json()
                data2.forEach(function(elem){
                    // Get WorkerId of BonusPayment-data
                    workerid = elem.WorkerId
                    bonus = elem.BonusAmount

                    //look through progressmodaltables rows and change bonus-td if workerIds match
                    $("table.progress-table tbody tr").each(function(){
                        if($(this).find(".worker").text() == workerid)
                            $(this).find(".bonus").text(bonus)
                    })
                })

            }        
        })

        $('#csvmodal').on('show.bs.modal', function(event){
            $("#uploadform #file").val('').removeClass("error")
            $("#uploadform label.error").empty()
            $("#uploadform div.error").empty()
            $("#uploadform div.success").empty()             

            var modal = $(this)
            var button = $(event.relatedTarget)
            tbody = modal.find(".modal-body tbody").empty()
            modal.find("#qual-empty").empty()
            row = button.closest('tr.info-row').prev()
            data = table.row(row).data()
            $("#hit_batched").val(data.batched)
            $("#hit_identifier").val(data.batched?data.batch_id:data.HITId)
            modal.find(".modal-title").text("CSV Actions for " + data.Title)
            if (data.batched)
                href = "/export/"+data.batch_id
            else
                href = "/export/"+data.HITId
            
            $("#export-all").attr("href", href+"/all")
            $("#export-submitted").attr("href", href+"/submitted")
        })

        $('#qualmodal').on('show.bs.modal', function(event){
            var modal = $(this)
            var button = $(event.relatedTarget)
            tbody = modal.find(".modal-body tbody").empty()
            modal.find("#qual-empty").empty()
            row = button.closest('tr.info-row').prev()
            data = table.row(row).data()
            modal.find(".modal-title").text("Qualifications for " + data.Title)
            // Iterate over each Qualification of HIT
            
            if(!data.QualificationRequirements.length){
                row = $('<div class="row p-5">')
                row.append('<div class="col-lg-12 text-center"><h2>No Qualifications are assigned to this HIT</h2></div>')
                modal.find("#qual-empty").append(row)
            }else{
                data.QualificationRequirements.forEach(function(elem, index){
                    table_qual_id = elem.QualificationTypeId
                    value = "-"
    
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
    
                    qual_row = $('<tr>').addClass("border-bottom")
                    .append($('<td>').append($("<div>").text(index+1+".")))
                    //.append($('<td>').append($("<div>").text(table_qual_id)))
                    .append($('<td>').addClass("qual-name").text("Batch-Qualification, reload the Page to show the actual Name"))
                    .append($('<td>').text(elem.Comparator))
                    .append($('<td>').text(value))
                    .append($('<td>').text(elem.ActionsGuarded))
                    //Check if Id is of adult or master type
                    if(table_qual_id == master_id){
                        qual_row.find(".qual-name").text('Masters')
                    }else if(table_qual_id == master_id_sandbox){
                        qual_row.find(".qual-name").text('Masters Sandbox')
                    }else if(table_qual_id == adult_id){
                        qual_row.find(".qual-name").text('Adult Content')
                    }else{
                        //loop over all qualifications to get the name
                        for(i in quals){
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
                $("#uploadform label.error").append("This field is required.")                
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
                row = $("<div>").addClass("row")
                col = $("<div>").addClass("col-3")
                row_one = row.clone()
                row_one.append(col.clone().text("Approved"))
                        .append(col.clone().text(json.data.approved))
                        .append(col.clone().text("Rejected"))
                        .append(col.clone().text(json.data.rejected))

                row_two = row.clone()                        
                row_two.append(col.clone().text("Bonus paid"))
                        .append(col.clone().text("$"+json.data.bonus))
                        .append(col.clone().text("Softblocked"))
                        .append(col.clone().text(json.data.softblocked))
                
                $("#uploadform div.success").append(row_two).append(row_one)
                
                // Adding warnings if any
                // Why do Dicts in JS not have an inbuilt method to check if empty, or atleast a length?
                if(Object.keys(json.warnings).length > 0){
                    $("#uploadform div.error").append('<h4>Warnings:<h4>')
                    for (i in json.warnings){
                        console.log(i)
                        li = $('<li>').text("Row "+i)
                        ul = $('<ul>')
                        for (j in json.warnings[i]){
                            row_li = $('<li>').text(json.warnings[i][j])
                            ul.append(row_li)
                        }
                        $("#uploadform div.error").append($('<ul>').append(li.append(ul)))                                
                    }
                }
            }else{
                $("#uploadform label.error").empty()
                $("#uploadform div.error").empty()
                //$(this).prop("disabled",false);
                $("#uploadform #file").addClass("error")
                if(json.errortype == 'main'){
                    $("#uploadform div.error").append('<h4>'+json.errors.main+'</h4>')
                }else if(json.errortype == 'document'){
                    $("#uploadform div.error").append('<h4>Logic-error in CSV<h4>')
                    for (i in json.errors){
                        li = $('<li>').text("Row "+i)
                        ul = $('<ul>')
                        for (j in json.errors[i]){
                            row_li = $('<li>').text(json.errors[i][j])
                            ul.append(row_li)
                        }
                        $("#uploadform div.error").append($('<ul>').append(li.append(ul)))
                        
                    }
                }else if(json.errortype == 'form'){
                    for(i in json.errors)
                        $("#uploadform label.error").append(json.errors[i]+'<br/>')
                }
            }
        })             
        

    $.fn.dataTable.ext.type.order['amount-complete-pre'] = function ( data ) {
        percentage = data.substring(data.indexOf(" (")+2, data.indexOf("%)")) // isolate percentage
        return percentage
    };

    

    function format_info ( data ) { 
        

        container = $("<div class='container' style='float-left'>")

        if(data.batched){
            qualificationbutton = '<button type="button" class="btn btn-sm btn-info" data-toggle="modal" data-target="#qualmodal">CLICK</button>'
            hidebtn = '<button type="button" class="btn btn-info hide_hit">'+ (data["hidden"]?"Show":"Hide") +'</button>'         
            csv_modal_btn = '<button type="button" class="btn btn-info" data-toggle="modal" data-target="#csvmodal">CSV-Actions</button>'
            group_id = data.batch_id
            query = data.batch_id+'/True'
            toggle_status_btn = '<button type="button" class="btn btn-info toggle-groupstatus">'+ (data["batch_status"]?"Pause":"Continue") +'</button>'
            cache_btn = '<button type="button" class="btn btn-info cache-btn">Cache</button>'
            batch_status = data['batch_status'] ? 'Active':'Paused'
            row_one = $('<div class="row mt-2">'+
                '<div class="col-2">Title:</div>'+
                '<div class="col-2">'+data['Title']+'</div>'+
                '<div class="col-2">Reward:</div>'+
                '<div class="col-4">'+data['Reward']+'</div>'+
                '<div class="col-2">'+csv_modal_btn+'</div>'+
            '</div>')

            row_two = $('<div class="row mt-2">'+
                '<div class="col-2">Description:</div>'+
                '<div class="col-2">'+data['Description']+'</div>'+
                '<div class="col-2">MiniBatched:</div>'+
                '<div class="col-4">'+data['batch_id']+'</div>'+
                '<div class="col-2">'+cache_btn+'</div>'+
            '</div>')

            row_three = $('<div class="row mt-2">'+
                '<div class="col-2">Keywords:</div>'+
                '<div class="col-2">'+data['Keywords']+'</div>'+
                '<div class="col-2 ">Batch-Status:</div>'+
                '<div class="col-4 batch-status">'+batch_status+'</div>'+
                '<div class="col-2">'+toggle_status_btn+'</div>'+
            '</div>')

            row_four = $('<div class="row mt-2">'+
                '<div class="col-2">Qualifications:</div>'+
                '<div class="col-2">'+qualificationbutton+'</div>'+
                '<div class="col-2">HITTypeId:</div>'+
                '<div class="col-4">'+data['HITTypeId']+'</div>'+
                '<div class="col-2">'+hidebtn+'</div>'+
            '</div>')
        }
        else{
            qualificationbutton = '<button type="button" class="btn btn-sm btn-success" data-toggle="modal" data-target="#qualmodal">CLICK</button>'
            hidebtn = '<button type="button" class="btn btn-success hide_hit">'+ (data["hidden"]?"Show":"Hide") +'</button>'         
            csv_modal_btn = '<button type="button" class="btn btn-success" data-toggle="modal" data-target="#csvmodal">CSV-Actions</button>'
            query = data.HITId

            row_one = $('<div class="row mt-2">'+
                '<div class="col-2 mt-2">Description:</div>'+
                '<div class="col-2 mt-2">'+data['Description']+'</div>'+
                '<div class="col-2 mt-2">HITId:</div>'+
                '<div class="col-4 mt-2">'+data['HITId']+'</div>'+
                '<div class="col-2 mt-2">'+csv_modal_btn+'</div>'+
            '</div>')

            row_two = $('<div class="row mt-2">'+
                '<div class="col-2 mt-2">Keywords:</div>'+
                '<div class="col-2 mt-2">'+data['Keywords']+'</div>'+
                '<div class="col-2 mt-2">HITTypeId:</div>'+
                '<div class="col-4 mt-2">'+data['HITTypeId']+'</div>'+
            '</div>')

            row_three = $('<div class="row mt-2">'+
                '<div class="col-2 mt-2">Reward:</div>'+
                '<div class="col-2 mt-2">'+data['Reward']+'</div>'+
                '<div class="col-2 mt-2">HIT-Status:</div>'+
                '<div class="col-4 mt-2">'+data['HITStatus']+'</div>'+
            '</div>')

            row_four = $('<div class="row mt-2">'+
                '<div class="col-2">Qualifications:</div>'+
                '<div class="col-2">'+qualificationbutton+'</div>'+
                '<div class="col-2">MiniBatched:</div>'+
                '<div class="col-4">'+false+'</div>'+
                '<div class="col-2">'+hidebtn+'</div>'+
            '</div>')
            
        }
        return container.append(row_one).append(row_two).append(row_three).append(row_four)
    }

    function format_slide ( data ) {
        // `d` is the original data object for the row
        group_id = data.batch_id
        data = data.minihits
        $table = $(' <table cellpadding="5" cellspacing="0" border="0" style="padding-left:50px;">').addClass('minihit-table')
        $table.data('group-id', group_id)
        
        for(i in data){
            hit = data[i]
            $row = format_slide_row(hit)
            $table.append($row)
        }
        $slider = $('<div>').addClass('slider').append( $table)
        return $slider
    }

    function format_slide_row(hit){
        if(hit.hasOwnProperty('CreationTime')){
            ass_submitted = hit.MaxAssignments - (hit.NumberOfAssignmentsAvailable + hit.NumberOfAssignmentsPending)

            $tr = $('<tr class="minihitrow running">')
            $tr.append($('<td>').text(hit.position)) //hit.position should be same as i always
            $tr.append($('<td>').text(hit.HITStatus))
            $tr.append($('<td>').text(ass_submitted+'/'+hit.MaxAssignments+' , P: '+hit.NumberOfAssignmentsPending+', C: '+hit.NumberOfAssignmentsCompleted))
            $tr.append($('<td>').text(hit.CreationTime))
            $tr.append($('<td>').text(hit.Expiration))
            $progressbtn = $('<button type="button" data-toggle="modal" data-target="#progressmodal">').data("id",hit.HITId).data("position",hit.position)
                .addClass("btn btn-sm btn-info").append('<i class="fas fa-tasks"></i>')
            $tr.append($('<td>').append($progressbtn))
        }else{
            $tr = $('<tr class="minihitrow queued">')
            $tr.append($('<td>').text(hit.position)) //hit.position should be same as i always
            $tr.append($('<td>').text('Queued'))
            $tr.append($('<td>').text('0/'+hit.workers))
            $tr.append($('<td>'))
            $tr.append($('<td>'))
            $delbtn = $('<button type=button>').addClass("btn btn-sm btn-danger delete-queued").append('<i class="fa fa-trash"></i>')                   

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
        hitgroup = {}
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
        for (i = 0; i < array.length; i++){
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
        for(item_index in json){
            item = json[item_index]
            if(item.hasOwnProperty(key) && item[key] == value){
                return item
            }
        }
        return null
    }

    function get_elements_with_value(json, key, value){
        list = []
        json.forEach((item) => {
            if(item.hasOwnProperty(key) && item[key] == value)
                list.push(item) 
        });
        return list
    };
