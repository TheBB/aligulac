toggle_block = (id) ->
    $(".lm[data-id=#{id}]").toggle()
    $(".lma[data-id=#{id}]").html(
        if $(".lma[data-id=#{id}]").html() == autocomp_strings['hide']
            autocomp_strings['show']
        else
            autocomp_strings['hide']
    )
    false

lm_toggle_visibility = (id) ->
     $("#fix" + id).toggle()
     $("#inp" + id).toggle()
     $("#" + id + "_1").focus()
     false

check_boxes = (id) ->
    $("input[data-match=#{id}]").prop('checked', true)
    false

uncheck_boxes = (id) ->
    $("input[data-match=#{id}]").prop('checked', false)
    false

module.exports.Common = Common =
    init: () ->
        $('.lma').click ->
            toggle_block $(this).data('id')
        $('.lmp').click ->
            lm_toggle_visibility $(this).data('id')

        $('.check-boxes-btn').click ->
            check_boxes $(this).data('match')

        $('.uncheck-boxes-btn').click ->
            uncheck_boxes $(this).data('match')
