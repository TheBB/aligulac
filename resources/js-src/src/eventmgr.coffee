modify = (pid, pname, ptype) ->
    $('#parent_id_field').val(pid)
    $('#id_type').val(
        switch ptype
            when 'round' then 'round'
            when 'event' then 'round'
            when 'category' then 'category'
    )
    $('#parent_name').html(pname)
    $('#md-eventmgr').modal()

module.exports.EventMgr = EventMgr =
    init: () ->
        $('.tree-toggle').click () ->
             $(this).parent().parent().next('.subtree').toggle(100)
             false

        $('#root_btn').click () ->
            $('input[id=parent_id_field]').val('-1')
            $('#parent_name').html('Root (N/A)')
            $('#md-eventmgr').modal()
            false

        $('#showguide').click () ->
            $('#guide').collapse();
            $('#showguide').toggle();

        $('.event-modify-button').click () ->
            name = $(this).data('event-fullname')
            id = $(this).data('event-id')
            type = $(this).data('event-type')
            modify id, name, type

        $('#id_predef_names').change () ->
            if $('#id_predef_names').prop('selectedIndex') > 0
                $('#id_custom_names').val('')
                $('#id_type').val('round')

        $('#id_custom_names').keypress () ->
            if $('#id_custom_names').val() != ''
                $('#id_predef_names').prop('selectedIndex', 0)
