# General
is_descendant = (par, child) ->
    node = child
    while node?
        if node == par
            return true
        else
            node = node.parentNode
    return false

set_textbox = (id, s) ->
    $("#" + id)[0].value = s

set_textarea_line = (id, s, line) ->
    cur = $("#" + id)[0].value.replace /\r\n/, '\n'
    a = cur.split '\n'
    a[line] = s
    $("#" + id)[0].value = a.join '\n'

# Visibility toggling
togvis = (id, visible) ->
    $("#" + id).toggle()

togvis_tbody = (id) -> togvis id
togvis_span = togvis_tbody
togvis_div = togvis_span

switch_to = (id, all) ->
    for cid in all
        if cid == id
            $("#" + cid).show()
        else
            $("#" + cid).hide()

switch_tab = (id, all) ->
    for tabid in all
        if tabid == id
            $("#" + tabid).show()
            $("##{ tabid }-tab").attr('class', 'tabsel')
        else
            $("#" + tabid).hide()
            $("##{ tabid }-tab").attr('class', 'tabunsel')

toggle_form = (id) -> $("#" + id).show()
hide_charts = -> $("#chart").hide()

togHTML = (id, a, b) ->
    d = $("#" + id)
    if d.html().trim() == a
        d.html b
    else
        d.html a

# Checkbox toggling
mark_all = (val, prefix) ->
    $('input:checkbox').each (i, e) ->
        if prefix == '' or 0 == $(e).name.indexOf prefix
            $(e).checked = val
