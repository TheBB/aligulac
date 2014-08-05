toggle_pp_players = (id) ->
    $("[data-placement=#{ id }]").toggle()
    false

module.exports.EventRes = EventRes =
    init: () ->
        $(".pp_showbtn").click ->
            toggle_pp_players $(this).data('placement')
