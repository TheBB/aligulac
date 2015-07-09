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

check_all_boxes = () ->
    $('input[name|="match"]').prop('checked', true)
    false

uncheck_all_boxes = () ->
    $('input[name|="match"]').prop('checked', false);
    false

check_boxes = (id) ->
    $("input[data-match=#{id}]").prop('checked', true)
    false

uncheck_boxes = (id) ->
    $("input[data-match=#{id}]").prop('checked', false)
    false

module.exports.create_tag = (tag) ->
    $(document.createElement(tag))

module.exports.Common = Common =
    init: () ->
        $('.langbtn').click ->
            $(this).closest('form').submit()

        $('.lma').click ->
            toggle_block $(this).data('id')
        $('.lmp').click ->
            lm_toggle_visibility $(this).data('id')

        $('.check-boxes-btn').click ->
            check_boxes $(this).data('match')

        $('.uncheck-boxes-btn').click ->
            uncheck_boxes $(this).data('match')

        $('.check-all-btn').click check_all_boxes
        $('.uncheck-all-btn').click uncheck_all_boxes

        # Ambiguity resolver for tagsinput
        $('.not-unique-more').click ->
            $(this).toggle()
            $(this).parent().find('.not-unique-hidden-names').toggle()
            false

        $('.not-unique-update-player').click ->
            _this = $(this)
            update = _this.data('update')
            updateline = _this.data('updateline')
            tag = _this.data('tag')
            id = _this.data('id')
            input = $("##{ update }")

            taglist = input.getTags()
            taglist[updateline] = tag + " " + id
            input.importTags(taglist.join '\n')

            _this.closest('.message').toggle()
            false
