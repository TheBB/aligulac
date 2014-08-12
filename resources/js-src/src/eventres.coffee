changed_story = ->
    idx = $('#extantstories').prop('selectedIndex')
    data = story_data[idx]
    $('#story_id').prop('value', data['idx'])
    $('#id_player').prop('value', data['player'])
    $('#st_date').datepicker('setDate', data['dt'])
    $('#id_text').prop('selectedIndex', data['text'])
    $('#id_params').prop('value', data['params'])
    $('#storynewbtn').prop('disabled', idx > 0)
    $('#storyupdbtn').prop('disabled', idx == 0)
    $('#storydelbtn').prop('disabled', idx == 0)

get_order = ->
    list = $("#sortable").sortable("toArray")
    $('#order').prop('value', list.join(','))

toggle_pp_players = (id) ->
    $("[data-placement=#{ id }]").toggle()
    false

module.exports.EventRes = EventRes =
    init: () ->
        $(".pp_showbtn").click ->
            toggle_pp_players $(this).data('placement')

        # This is just for convenience
        if admin? and admin
            if story_data?
                $('#extantstories').change changed_story

            if has_children? and has_children
                $("#sortable").sortable()
                $("#sortable").disableSelection()
                $('#submit-order').click get_order
