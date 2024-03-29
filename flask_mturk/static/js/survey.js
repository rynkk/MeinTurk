$('#previewButton').on('click', function(){
    var popup = window.open("","Preview","width=800,height=600,scrollbars=1,resizable=1")
    var start = '<!DOCTYPE html><html><head><title>HIT</title><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/><script type="text/javascript" src="https://s3.amazonaws.com/mturk-public/externalHIT_v1.js"><\/script></head><body><form name="mturk_form" method="post" id="mturk_form" action="https://www.mturk.com/mturk/externalSubmit"><input type="hidden" value="" name="assignmentId" id="assignmentId" />'
    var html = CKEDITOR.instances.editor_field.getData()
    var end = '<p class="text-center"><input type="submit" id="submitButton" class="btn btn-primary" value="Submit" /></p></form><script language="Javascript">turkSetAssignmentID();<\/script></body></html>'
    
    popup.document.open()
    popup.document.write(start+html+end)
    popup.document.close()

})

$("form input").on('keypress', function(e) {
    return e.which !== 13;
});

$("#sform").on('blur', 'input, select', function() {
    $(this.form).validate().element(this)
    var page = $(this).closest('.tab-pane')

    if(page.find('select, input').hasClass('error')){
        $('a[href="#'+page.attr("id")+'"').addClass('error')
    }else{
        $('a[href="#'+page.attr("id")+'"').removeClass('error')
    }

});

jQuery.validator.addMethod("qualNameUniqueNaive", function(value) {
    for (var i in qualifications){
        if(qualifications[i]['Name'] == value || softblock_name == value){
            return false
        }
    }
    return true
}, _("Qualification Name Already Exists!"));

jQuery.validator.addMethod("disallowSelectOption", function(value, element) {
    if(value == 'false'){
        return false
    }
    return true
}, _("Please select a valid option."));


$("#sform").validate({
    ignore: "",
    invalidHandler: function(e, validator){
        if(validator.errorList.length){
            $('#tabs a[href="#' + $(validator.errorList[0].element).closest(".tab-pane").attr('id') + '"]').tab('show')
            for (var i=0; i<validator.errorList.length; i++){
                $('#tabs a[href="#' + $(validator.errorList[i].element).closest(".tab-pane").attr('id') + '"]').addClass('error')
            }
        }
    },
    rules : {
        qualification_name : { qualNameUniqueNaive : true }
    },
    errorPlacement: function(error, element) {
        if  ($(element).hasClass('selector') )
            error.insertAfter(element.closest('.selectorrow').find('.removediv'));
        else
            error.insertAfter(element);
    },
    submitHandler: function(form, event){
        $('body').addClass("loading")
        $("#loading-main").text(_("Please wait while your Survey is being created!"))
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
        var full_string = (full==0 ? "" : full+"x9")

        var part = amount%9
        var part_string = (part==0 ? "" : "1x"+part)

        var connector = ((full_string!="" && part_string!="") ? _(" and "):"")
        
        var text = ":  " + gt.strargs(_("The Survey will be split into %1 %2 %3 HITs."), [full_string, connector, part_string])

        $("#batches").text(text)
        $("#batches").show()
    }        
}
$('a[data-toggle="tab"][href="#p5"]').on('shown.bs.tab', function (e) {

    var batched = document.getElementById('minibatch').checked
    if (batched){
        $('#overview_minibatch').text(_("enabled"))
                                .addClass("text-success")
                                .removeClass("text-danger")
        $('#overview_name').text($('#project_name').val()==''?'-':$('#project_name').val())
    }else{
        $('#overview_minibatch').text(_("disabled"))
                                .addClass("text-danger")
                                .removeClass("text-success")
        $('#overview_name').text(_('***Ignored for non-batched***'))
    }

    $('#overview_title').text($('#title').val()==''?'-':$('#title').val())
    var masters = $('input[name="must_be_master"]:checked').val()=='yes'
    $('#overview_masters').text(masters?'':_('not'))

    var workers = parseInt($('#amount_workers').val())
    if (isNaN(workers)){
        workers = 0
        hits = 0
    }else{
        if(batched)
            hits = Math.ceil(workers / 9)
        else
            hits = 1
    }
    $('#overview_hits').text(hits)
    $('#overview_workers').text(workers)

    $('#overview_lifetime').text($("#time_till_expiration-int_field").val()+" "+$("#time_till_expiration-unit_field").children("option:selected").text())
    $('#overview_allotted_time').text($("#allotted_time_per_worker-int_field").val()+" "+$("#allotted_time_per_worker-unit_field").children("option:selected").text())
    $('#overview_time_approval').text($("#accept_pay_worker_after-int_field").val()+" "+$("#accept_pay_worker_after-unit_field").children("option:selected").text())

    var quals_text=""
    $('#qualifications select.selector').each(function(){
        if($(this).find("option:selected").val() != 'false'){            
            quals_text += $(this).find("option:selected").text()+"; "
        }
    })
    if (quals_text == "")
        quals_text = _('None')
    
    $('#overview_qualifications').text(quals_text)

    var reward = parseFloat($('#payment_per_worker').val())
    
    var costs = calculate_cost(batched, masters, reward, workers)
    $('#overview_reward').text(costs['reward_each'].toFixed(2))
    $('#overview_fees').text(costs['fee_each'].toFixed(2))
    $('#overview_fees_percentage').text(costs['fee_percentage'])
    $('#overview_ass_total').text(costs['ass_total'].toFixed(2))
    $('#overview_nrass').text(workers)
    $('#overview_total').text(costs['total_cost'].toFixed(2))
    $('#overview_saved').text(costs['saved'].toFixed(2))
})

function calculate_cost(batched, masters, reward, workers){
    // standard fee is 20%
    var fee = 0.2
    var fee_reasons="batched"
    if(!batched){
        // Additional 20% fees if more than 9 workers for a HIT (nonbatched) 
        if(workers>9){
            fee += 0.2        
            fee_reasons=_("non-batched")
        }else{
            fee_reasons=_("non-batched, <9 workers")
        }
    }
    // Masters increases the fee by additional 5%
    if(masters){
        fee+=0.05
        fee_reasons+=", " + _("masters")
    }
    var fee_each = reward * fee
    var total_fees = reward * fee * workers
    var fee_percentage = fee * 100
    var reward_each = reward
    var ass_total = reward_each + fee_each
    var total_reward = reward * workers
    var total_cost = total_reward + total_fees
    
    var normal_fee = 0.2
    if (workers > 9)   
        normal_fee = 0.4
    if(masters)
        normal_fee += 0.05

    var total_saved = (normal_fee * reward + reward) * workers - total_cost
    
    return {'fee_percentage':fee_percentage, 'fee_reasons': fee_reasons, 'fee_each': fee_each, 'ass_total': ass_total,
            'total_fees': total_fees, 'reward_each': reward_each, 'total_reward': total_reward, 'total_cost': total_cost, 'saved': total_saved}
}

$(".next").click(function () {
    var parent_id = $(this).parent().parent().parent().attr("id")
    var int_id = parseInt(parent_id.substr(1))
    var next_id = "#p" + (int_id + 1)
    $(".nav .nav-item[href='" + next_id + "']").trigger("click")
});

$(".prev").click(function () {
    var parent_id = $(this).parent().parent().parent().attr("id")
    var int_id = parseInt(parent_id.substr(1))
    var prev_id = "#p" + (int_id - 1)
    $(".nav .nav-item[href='" + prev_id + "']").trigger("click")
});

$('i[data-toggle="tooltip"]').tooltip()

var all_options=[];
var sys_group = $("<optgroup label="+_('System')+"></optgroup>")
var custom_group =$("<optgroup label="+_('Own')+"></optgroup>")

qualifications.forEach(function (obj) {
    var option_type = obj.Type ? 'system' : 'custom'
    var option = {
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
$("#payment_per_worker").attr('max', max_payment)

var added=0
$("button#add-system").click(function(){
    if(added==0){
        all_options.forEach(function(obj){
            if (obj.type=="custom")
                return
            
            $(".selector").each(function(i, elem){
                var elem = $(elem)
                if(elem.val() == obj.id)
                    elem.closest('.row').remove()
            })
            var $row = create_qual_row()
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
    var $row = create_qual_row()
    $("#qualifications .row:last").before($row)
    rearrange_ids()
    enable_disable_selected()
});

$('#qualifications').on('click','.remove-row', function(){
    $(this).parents('.row').remove();
    rearrange_ids()
    enable_disable_selected()
})

$('#qualifications').on('change','.own-select', function(){
    if($(this).val() == "EqualTo" || $(this).val() == "NotEqualTo")
        $(this).parent().next(".value").show()
    else
        $(this).parent().next(".value").hide()
})

function create_qual_row(){
    var btn = $("<a class='remove-row'><i class='fas fa-trash-alt'></i></a>")
    var row = $("<div class='row selectorrow'></div>")
    var col0= $("<div class='col-auto'><p class='index'>X</p></div>")
    var col1= $("<div class='col-auto'></div>")
    var col2= $("<div class='col-auto comparator'></div>")
    var col3= $("<div class='col-auto value'></div>")
    var col4= $("<div class='col-auto removediv'></div>")

    var select1 = $("<select id='qualifications_select-selects-X-selector' class='selector'></select>")
    var select2 = $("<select id='qualifications_select-selects-X-first_select'></select>")
    var select3 = $("<select id='qualifications_select-selects-X-second_select'></select>")

    select1.on("change", function(){
        show_selects_for_option($(this))
        enable_disable_selected()
    })

    var option = $("<option value='false'>---"+_("Select")+"---</option>")
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

    // Add rules for dynamic qualification fields on submit
    $('#qualifications .selector').each(function() {
        $(this).rules("add", 
            {
                disallowSelectOption : true
            });
    });
}


function show_selects_for_option($selected){

    var $parent = $selected.closest(".selectorrow")
    var $comparator_col = $parent.find(".comparator")
    var $value_col = $parent.find(".value")

    var $comparator_select = $comparator_col.children("select")
    var $value_select = $value_col.children("select")
    
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
        $comparator_select.addClass("own-select")
        var $option0 = $("<option value='Exists'>"+_("Exists")+"</option>")
        var $option1 = $("<option value='DoesNotExist'>"+_("Does Not Exist")+"</option>")
        var $option2 = $("<option value='EqualTo'>"+_("Equal To")+"</option>")
        var $option3 = $("<option value='NotEqualTo'>"+_("Not Equal To")+"</option>")
        $comparator_select.append($option0)
                          .append($option1)
                          .append($option2)
                          .append($option3)
    }else{
        options.comparators.forEach(comparator => {
            var $option = $("<option value="+comparator.value+">"+comparator.name+"</option>")
            $comparator_select.append($option)
        })                 
    }

    $comparator_col.show() //comparator is always shown (unless ---SELECT---)
    switch(options.value){
        case "PercentValue":
            for(let i=100;i>=0;i-=percentage_interval)
                $value_select.append($('<option></option>').val(i).html(i))    
            $value_col.show()     
            break;
        case "IntegerValue":
            for(let i=0;i<integer_list.length;i++)
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
            for(let i=0;i<100;i++)
                $value_select.append($('<option></option>').val(i).html(i))   
            break;

    }
    if(options.default){
        $comparator_select.val(options.default.comparator)
        $value_select.val(options.default.val)
    }
}

function enable_disable_selected(){
    var selected_options = [];

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
