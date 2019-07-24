    $('#previewButton').on('click', function(){
        var popup = window.open("","Preview","width=800,height=600,scrollbars=1,resizable=1")
        start = '<!DOCTYPE html><html><head><title>HIT</title><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/><script type="text/javascript" src="https://s3.amazonaws.com/mturk-public/externalHIT_v1.js"><\/script></head><body><form name="mturk_form" method="post" id="mturk_form" action="https://www.mturk.com/mturk/externalSubmit"><input type="hidden" value="" name="assignmentId" id="assignmentId" />'
        html = CKEDITOR.instances.editor_field.getData()
        end = '<p class="text-center"><input type="submit" id="submitButton" class="btn btn-primary" value="Submit" /></p></form><script language="Javascript">turkSetAssignmentID();<\/script></body></html>'
        
        popup.document.open()
        popup.document.write(start+html+end)
        popup.document.close()

    })

        $('form input').on('keypress', function(e) {
            return e.which !== 13;
        });

        $("#sform input").blur(function() {
            $(this.form).validate().element(this);
        });

        $("#sform").validate({
            ignore: "",
            invalidHandler: function(e, validator){
                if(validator.errorList.length)
                    $('#tabs a[href="#' + $(validator.errorList[0].element).closest(".tab-pane").attr('id') + '"]').tab('show')
            },
            submitHandler: function(form, event){
                $('body').addClass("loading")
                $(".loading-modal > p").text("Please wait while your Survey is being created!")
                form.submit()
            }
        });

    $('form#sform').find('input').each(function(){
        var $input = $(this)
        var $label = $("label[for='"+$input.prop('id')+"']")
        if($input.prop('required') || $input.prop('id')=='starting_date'){ //if starting_date is shown it is required
            if($label.length != 0)
                $label.text($label.text()+"*")
        }
    });
    
    $(".mbqual").toggle($('#minibatch').prop("checked"));   //if page reloaded after submit make sure that mbqual is set appropriately
    if($('#minibatch').prop("checked"))                     //if page reloaded after submit make sure that batches is set appropriately
        print_batches()

    $('#minibatch').on('change', function() {
        $(".mbqual").toggle(this.checked);
        this.checked?print_batches():$("#batches").hide()
    });
     
    $("#amount_workers").on('input', function(){
        var minibatch_box = $("#minibatch")
        if($(this).val()<10){
            minibatch_box.prop("disabled", true)
            minibatch_box.prop("checked", false)
            $("#batches").hide()
            $(".mbqual").hide()
        }else{
            minibatch_box.removeAttr("disabled")
            if(minibatch_box.is(':checked'))
                print_batches()
        }
    });

    function print_batches(){
        var amount =  $("#amount_workers").val()
        if (amount!=0){
            var full = Math.floor(amount/9)
            var full_string = (full==0 ? "" : full+"x9er")

            var part = amount%9
            var part_string = (part==0 ? "" : "1x"+part+"er")

            var connector = ((full_string!="" && part_string!="") ? " und ":"")
            
            var text = ":  The Survey will be split into " + full_string + connector + part_string + " parts."

            $("#batches").text(text)
            $("#batches").show()
        }        
    }

    $(".next").click(function () {
        parent_id = $(this).parent().parent().parent().attr("id")
        int_id = parseInt(parent_id.substr(1))
        next_id = "#p" + (int_id + 1)
        $(".nav .nav-item[href='" + next_id + "']").trigger("click")
    });

    $(".prev").click(function () {
        parent_id = $(this).parent().parent().parent().attr("id")
        int_id = parseInt(parent_id.substr(1))
        prev_id = "#p" + (int_id - 1)
        $(".nav .nav-item[href='" + prev_id + "']").trigger("click")
    });
    
    $('i[data-toggle="tooltip"]').tooltip()

    var all_options=[];
    var sys_group = $("<optgroup label='System'></optgroup>")
    var custom_group =$("<optgroup label='Own'></optgroup>")
    
    qualifications.forEach(function (obj) {
            option_type = obj.Type ? 'system' : 'custom'
            option = {
                'type': option_type,
                'id': obj.QualificationTypeId,
                'name': obj.Name,
                'comparators': obj.Comparators,
                'value': obj.Value,
                'default': obj.Default
            }
            all_options.push(option)

            option = $("<option value=" + obj.QualificationTypeId + ">" + obj.Name + "</option>")
            if (obj.Type == "system")
                sys_group.append(option)
            else
         custom_group.append(option)
    })
    $("#payment_per_worker").attr('max',max_payment)
    initDOMs()    
    
    function initDOMs(){
        var added=0
        $("button#add-system").click(function(){
            if(added==0){
                all_options.forEach(function(obj){
                    if (obj.type=="custom")
                        return
                    
                    $(".selector").each(function(i, elem){
                        elem = $(elem)
                        if(elem.val() == obj.id)
                            elem.closest('.row').remove()
                    })
                    $row = create_qual_row()
                    $row.addClass("system-row")
                    $row.find("select option[value="+obj.id+"]").prop('selected',true).trigger('change');
                    $("#qualifications .row:first").after($row)
                })
                $('button#add-system').addClass('btn-danger').removeClass('btn-success').html("Remove default qualifications")
            }else{
                $("#qualifications .system-row").remove()
                $('button#add-system').addClass('btn-success').removeClass('btn-danger').html("Add default qualifications")
            }
            rearrange_ids()
            added = !added
            
            enable_disable_selected()
        });
            
        // TODO: Hide visibility radios if no qualification was chosen
    
        $("button#add-select").click(function() { //reconstruct HTML to match wtform            
            $row = create_qual_row()
            $("#qualifications .row:last").before($row)
            rearrange_ids()
            enable_disable_selected()
        });

        $(document).on('click','.remove-row', function(){
            $(this).parents('.row').remove();
            rearrange_ids()
            enable_disable_selected()
        })

        function create_qual_row(){
            btn = $("<a class='remove-row'><i class='fas fa-trash-alt'></i></a>")
            row = $("<div class='row selectorrow'></div>")
            col0= $("<div class='col-auto'><p class='index'>X</p></div>")
            col1= $("<div class='col-auto'></div>")
            col2= $("<div class='col-auto comparator'></div>")
            col3= $("<div class='col-auto value'></div>")
            col4= $("<div class='col-auto'></div>")

            select1 = $("<select id='qualifications_select-selects-X-selector' class='selector'></select>")
            select2 = $("<select id='qualifications_select-selects-X-first_select'></select>")
            select3 = $("<select id='qualifications_select-selects-X-second_select'></select>")

            select1.on("change", function(){
                show_selects_for_option($(this))
                enable_disable_selected()
            })

            option = $("<option value='false'>---Select---</option>")
            select1.append(option)
            select1.append(sys_group.clone())
            select1.append(custom_group.clone())
            col1.append(select1)
            col2.append(select2)
            col3.append(select3)
            col4.append(btn)
            row.append(col0)
            row.append(col1)
            row.append(col2)
            row.append(col3)
            row.append(col4)
            col2.hide() // Hide comparator by default
            col3.hide() // Hide values by default
            return row
        }


        function rearrange_ids(){
            $('#qualifications .selectorrow').each(function (index) {
                $(this).find('.index').text(index+1)
                $(this).find('select').each(function (){
                    var $selector = $(this)
                    var new_id = $selector.prop("id").replace(/\d+|X/g, index)  // RegEx: Gets number or X  (combination too, but w/e)
                    $selector.prop("id", new_id)
                    $selector.prop("name", new_id)
                })
            });
        }


        function show_selects_for_option($selected){

            $parent = $selected.closest(".selectorrow")
            $comparator_col = $parent.find(".comparator")
            $value_col = $parent.find(".value")

            $comparator_select = $comparator_col.children("select")
            $value_select = $value_col.children("select")
            
            $comparator_select.empty()
            $value_select.empty()
            
            $comparator_col.hide()
            $value_col.hide()

            if($selected.val()=='false') // If select ---SELECT---  return
                return            
            
            var options = all_options.find(option => option.id === $selected.val())

            if(!options)
                return
            
            if (options.comparators===undefined){   // Custom qualifications dont have the comparators-attribute set
                $option0 = $("<option value='Exists'>Exists</option>")
                $option1 = $("<option value='DoesNotExist'>Does Not Exist</option>")
                $comparator_select.append($option0)
                $comparator_select.append($option1)
            }else{
                options.comparators.forEach(comparator => {
                    $option = $("<option value="+comparator.value+">"+comparator.name+"</option>")
                    $comparator_select.append($option)
                })                 
            }

            $comparator_col.show() //comparator is always shown (unless ---SELECT---)

            switch(options.value){
                case "PercentValue":
                    for(i=100;i>=0;i-=percentage_interval)
                        $value_select.append($('<option></option>').val(i).html(i))    
                    $value_col.show()     
                    break;
                case "IntegerValue":
                    for (i=0;i<integer_list.length;i++)
                        $value_select.append($('<option></option>').val(integer_list[i]).html(integer_list[i]))      
                    $value_col.show()
                    break;
                case "LocaleValue":
                    for(let key in countrycodes){
                        if(countrycodes.hasOwnProperty(key)){
                            $value_select.append($('<option></option>').val(key).html(countrycodes[key]))
                        }
                    }
                    $value_col.show()
                    break;
                default:
                    break;

            }
            if(options.default){
                $comparator_select.val(options.default.comparator)
                $value_select.val(options.default.val)
            }
        }

            function enable_disable_selected(){
                selected_options = [];

                $(".selector").find(':selected').filter(function(idx, el) {
                    return $(el).attr('value');
                }).each(function(idx, el) {
                    selected_options.push($(el).attr('value'));
                });

                $(".selector").find('option').each(function(idx, option) { 
                    if (selected_options.indexOf($(option).attr('value')) > -1) {
                        if ($(option).is(':checked')) {
                            return;
                        } else {
                            $(this).attr('disabled', true);
                        }
                    } else {
                        $(this).attr('disabled', false);
                    }
                });
            }            
    }