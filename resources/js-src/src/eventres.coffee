# This file is used with eventres.djhtml
toggle_pp_players = (id) ->
    $("[data-placement=#{ id }]").toggle()
    false
