eventmgr_modify = (pid, pname, ptype) ->
    $('#parent_id_field').val(pid)
    $('#id_type').val(
        switch ptype
            when 'round' then 'round'
            when 'event' then 'round'
            when 'category' then 'category'
    )
    $('#parent_name').html(pname)
    $('#md-eventmgr').modal()

eventmgr_predef_change = () ->
    if ($('#id_predef_names').prop('selectedIndex') > 0)
        $('#id_custom_names').val('')
        $('#id_type').val('round')

eventmgr_custom_keypress = () ->
    if ($('#id_custom_names').val() != '')
        $('#id_predef_names').prop('selectedIndex', 0)
