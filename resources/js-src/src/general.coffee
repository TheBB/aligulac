toggle_block = (id) ->
    $('#lm-' + id).toggle()
    $('#lma-' + id).html(
        if $('#lma-' + id).html() == autocomp_strings['hide']
            autocomp_strings['show']
        else
            autocomp_strings['hide']
    )
